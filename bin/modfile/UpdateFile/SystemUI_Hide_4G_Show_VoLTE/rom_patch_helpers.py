#!/usr/bin/env python3
from __future__ import annotations

import shutil
import subprocess
import zipfile
from pathlib import Path

BUILD_IMAGES_REL = "build/baserom/images"
PROVISION_CANDIDATES = [
    "system_ext/priv-app/Provision/Provision.apk",
    "system_ext/system_ext/priv-app/Provision/Provision.apk",
    "product/priv-app/Provision/Provision.apk",
    "product/product/priv-app/Provision/Provision.apk",
]
MIUI_SYSTEMUI_CANDIDATES = [
    "system_ext/priv-app/MiuiSystemUI/MiuiSystemUI.apk",
    "system_ext/system_ext/priv-app/MiuiSystemUI/MiuiSystemUI.apk",
    "system_ext/app/MiuiSystemUI/MiuiSystemUI.apk",
    "system_ext/system_ext/app/MiuiSystemUI/MiuiSystemUI.apk",
]
BUILDPROP_CANDIDATES = [
    "system/build.prop",
    "system/system/build.prop",
    "product/build.prop",
    "product/product/build.prop",
    "system_ext/build.prop",
    "system_ext/system_ext/build.prop",
    "odm/build.prop",
    "odm/odm/build.prop",
]


def _project_root() -> Path:
    return Path(__file__).resolve().parents[4]


def _apktool_dir() -> Path:
    return _project_root() / "bin" / "apktool"


def find_file_in_rom(work_dir: Path, relative_candidates: list[str]) -> dict:
    bases = [work_dir, work_dir / BUILD_IMAGES_REL]
    searched: list[str] = []
    for base in bases:
        for rel in relative_candidates:
            candidate = base / rel
            candidate_str = str(candidate)
            if candidate_str not in searched:
                searched.append(candidate_str)
            if candidate.is_file():
                return {"found": True, "found_path": str(candidate), "searched_paths": searched, "reason": ""}
    return {"found": False, "found_path": None, "searched_paths": searched, "reason": f"Not found in {len(searched)} searched paths"}


def find_provision_apk(work_dir: Path) -> dict:
    return find_file_in_rom(work_dir, PROVISION_CANDIDATES)


def find_miui_systemui_apk(work_dir: Path) -> dict:
    return find_file_in_rom(work_dir, MIUI_SYSTEMUI_CANDIDATES)


def find_build_prop_files(work_dir: Path) -> list[dict]:
    bases = [work_dir, work_dir / BUILD_IMAGES_REL]
    seen: set[str] = set()
    results: list[dict] = []
    for base in bases:
        for rel in BUILDPROP_CANDIDATES:
            candidate = base / rel
            candidate_str = str(candidate)
            if candidate_str in seen:
                continue
            seen.add(candidate_str)
            if candidate.is_file():
                results.append({"found": True, "found_path": candidate_str, "rel": rel})
    return results


def _find_apktool() -> Path | None:
    candidates = [
        _apktool_dir() / "apktool.jar",
        _project_root() / "bin" / "tools" / "apktool.jar",
        _project_root() / "apktool.jar",
    ]
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    if _apktool_dir().is_dir():
        for jar in _apktool_dir().glob("apktool*.jar"):
            return jar
    return None


def find_apkeditor() -> Path | None:
    for name in ("apke.jar", "APKEditor.jar", "apkeditor.jar"):
        for base in (_apktool_dir(), _project_root() / "bin" / "tools"):
            candidate = base / name
            if candidate.is_file():
                return candidate
    return None


def find_smali_jar() -> Path | None:
    for name in ("smali-3.0.5.jar", "smali.jar", "smali-2.5.2.jar", "smali-baksmali-3.0.5.jar"):
        candidate = _apktool_dir() / name
        if candidate.is_file():
            return candidate
    return None


def decompile_apk(apk_path: Path, out_dir: Path) -> dict:
    apktool = _find_apktool()
    if apktool is None:
        return {"ok": False, "tool_path": None, "command": None, "stdout": "", "stderr": "", "reason": "apktool.jar not found"}
    cmd = ["java", "-jar", str(apktool), "d", "-f", str(apk_path), "-o", str(out_dir)]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        ok = result.returncode == 0 and out_dir.is_dir()
        return {
            "ok": ok,
            "tool_path": str(apktool),
            "command": " ".join(cmd),
            "stdout": result.stdout[-2000:] if result.stdout else "",
            "stderr": result.stderr[-2000:] if result.stderr else "",
            "reason": "" if ok else f"apktool exited rc={result.returncode}",
        }
    except Exception as exc:
        return {"ok": False, "tool_path": str(apktool), "command": " ".join(cmd), "stdout": "", "stderr": "", "reason": str(exc)}


def rebuild_apk(decompiled_dir: Path, out_apk: Path) -> dict:
    apktool = _find_apktool()
    if apktool is None:
        return {"ok": False, "tool_path": None, "command": None, "stdout": "", "stderr": "", "reason": "apktool.jar not found"}
    cmd = ["java", "-jar", str(apktool), "b", "-f", str(decompiled_dir), "-o", str(out_apk)]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        ok = result.returncode == 0 and out_apk.is_file()
        return {
            "ok": ok,
            "tool_path": str(apktool),
            "command": " ".join(cmd),
            "stdout": result.stdout[-2000:] if result.stdout else "",
            "stderr": result.stderr[-2000:] if result.stderr else "",
            "reason": "" if ok else f"apktool rebuild rc={result.returncode}",
        }
    except Exception as exc:
        return {"ok": False, "tool_path": str(apktool), "command": " ".join(cmd), "stdout": "", "stderr": "", "reason": str(exc)}


def restore_patched_file_in_place(rebuilt_path: Path, original_path: Path, expected_name: str) -> dict:
    result = {
        "original_path": str(original_path),
        "rebuilt_path": str(rebuilt_path),
        "restored_path": None,
        "expected_name": expected_name,
        "restored": False,
        "permission": None,
        "error": None,
        "cleanup_done": False,
    }
    if not rebuilt_path.is_file():
        result["error"] = f"rebuilt file not found: {rebuilt_path}"
        return result
    if rebuilt_path.name != expected_name:
        renamed = rebuilt_path.parent / expected_name
        try:
            if renamed.exists():
                renamed.unlink()
            rebuilt_path.rename(renamed)
            rebuilt_path = renamed
            result["rebuilt_path"] = str(renamed)
        except Exception as exc:
            result["error"] = f"rename failed: {exc}"
            return result
    try:
        original_path.parent.mkdir(parents=True, exist_ok=True)
        if original_path.exists():
            original_path.unlink()
        shutil.move(str(rebuilt_path), str(original_path))
        result["cleanup_done"] = True
        try:
            original_path.chmod(0o644)
            result["permission"] = "0644"
        except Exception as exc:
            result["permission"] = f"0644 (chmod failed: {exc})"
        result["restored"] = True
        result["restored_path"] = str(original_path)
        return result
    except Exception as exc:
        result["error"] = f"restore move failed: {exc}"
        return result


def rebuild_apk_smali_only(unpacked_dir: Path, original_apk: Path, out_apk: Path) -> dict:
    smali_jar = find_smali_jar()
    if smali_jar is None:
        return {"ok": False, "tool": None, "stdout": "", "stderr": "", "reason": "smali.jar not found"}

    smali_map: list[tuple[Path, str]] = []
    for directory in sorted(unpacked_dir.iterdir()):
        if not directory.is_dir():
            continue
        name = directory.name
        if name in ("smali", "smali_classes"):
            smali_map.append((directory, "classes.dex"))
        elif name.startswith("smali_classes"):
            suffix = name[len("smali_classes") :]
            smali_map.append((directory, f"classes{suffix}.dex"))

    if not smali_map:
        return {"ok": False, "tool": str(smali_jar), "stdout": "", "stderr": "", "reason": "No smali_classes* dirs found in unpacked_dir"}

    temp_dir = Path(out_apk.parent) / f"{out_apk.stem}_smali_tmp"
    shutil.rmtree(temp_dir, ignore_errors=True)
    temp_dir.mkdir(parents=True, exist_ok=True)
    all_stdout: list[str] = []
    all_stderr: list[str] = []
    try:
        compiled: list[tuple[Path, str]] = []
        for smali_dir, dex_name in smali_map:
            dex_out = temp_dir / dex_name
            run = subprocess.run(["java", "-jar", str(smali_jar), "a", str(smali_dir), "-o", str(dex_out)], capture_output=True, text=True, timeout=300)
            all_stdout.append(run.stdout[-500:])
            all_stderr.append(run.stderr[-500:])
            if run.returncode != 0 or not dex_out.is_file():
                return {"ok": False, "tool": str(smali_jar), "stdout": "\n".join(all_stdout), "stderr": "\n".join(all_stderr), "reason": f"smali compile failed for {smali_dir.name}: rc={run.returncode}"}
            compiled.append((dex_out, dex_name))

        replace_names = {dex_name for _, dex_name in compiled}
        with zipfile.ZipFile(str(original_apk), "r") as original_zip:
            with zipfile.ZipFile(str(out_apk), "w") as new_zip:
                for info in original_zip.infolist():
                    if info.filename in replace_names:
                        continue
                    new_zip.writestr(info, original_zip.read(info.filename))
                for dex_path, dex_name in compiled:
                    new_zip.write(str(dex_path), dex_name, compress_type=zipfile.ZIP_STORED)

        if not out_apk.is_file():
            return {"ok": False, "tool": str(smali_jar), "stdout": "", "stderr": "", "reason": "output APK not created"}
        return {"ok": True, "tool": str(smali_jar), "stdout": "\n".join(all_stdout), "stderr": "\n".join(all_stderr), "reason": ""}
    except Exception as exc:
        return {"ok": False, "tool": str(smali_jar), "stdout": "", "stderr": "", "reason": str(exc)}
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)
