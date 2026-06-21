#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import rom_patch_helpers as rph

WORK_DIR = Path(__file__).resolve().parents[4]
PATCH_NAME = "miuisystemui_hide_4g_show_volte"
SYSUI_TARGET_CLASSES = [
    "MiuiOperatorCustomizedPolicy",
    "MiuiCarrierTextController",
    "MiuiCellularIconVM$special$$inlined$combine$1$3",
    "MiuiMobileIconBinder$bind$1$1$10",
]
INTL_FLAG = "Lmiui/os/Build;->IS_INTERNATIONAL_BUILD:Z"


def _entry(target_class: str, target_file: str, *, found: bool, status: str, detail: str = "", error: str | None = None, searched_paths: list[str] | None = None, os_detection: str | None = None) -> dict:
    return {
        "patch_name": PATCH_NAME,
        "target_class": target_class,
        "target_file": target_file,
        "found": found,
        "status": status,
        "detail": detail,
        "error": error,
        "searched_paths": searched_paths or [],
        "os_detection": os_detection,
    }


def _iter_build_prop_paths(work_dir: Path) -> list[Path]:
    return [Path(item["found_path"]) for item in rph.find_build_prop_files(work_dir)]


def _detect_rom_os(work_dir: Path) -> str:
    for prop in _iter_build_prop_paths(work_dir):
        content = prop.read_text(encoding="utf-8", errors="ignore").lower()
        if "os3" in content or "hyperos3" in content or "ro.mi.os.version.release=os3" in content:
            return "OS3"
        if "os2" in content or "hyperos2" in content or "ro.mi.os.version.release=os2" in content:
            return "OS2"
        if "miui" in content and any(token in content for token in ("v14", "v13", "v12")):
            return "OS1"
    return ""


def _detect_rom_region(work_dir: Path) -> str:
    for prop in _iter_build_prop_paths(work_dir):
        content = prop.read_text(encoding="utf-8", errors="ignore")
        if "IS_INTERNATIONAL_BUILD=true" in content or "IS_GLOBAL_BUILD=true" in content or "ro.product.locale=en-US" in content:
            return "Global"
        if "ro.product.locale=zh-CN" in content or "IS_CN_BUILD=true" in content or "ro.miui.region=CN" in content:
            return "CN"
    return ""


def _collect_smali_dirs(unpacked_dir: Path) -> list[Path]:
    return sorted([path for path in unpacked_dir.iterdir() if path.is_dir() and path.name.startswith("smali")], key=lambda path: path.name)


def _find_smali_class(smali_dirs: list[Path], class_name: str) -> Path | None:
    for smali_dir in smali_dirs:
        for path in smali_dir.rglob(f"{class_name}.smali"):
            return path
    return None


def _extract_register(line: str) -> str | None:
    match = re.match(r"\s*sget-boolean\s+(v\d+|p\d+)\s*,", line)
    return match.group(1) if match else None


def _is_in_try_range(lines: list[str], line_idx: int) -> bool:
    for idx in range(line_idx - 1, -1, -1):
        stripped = lines[idx].strip()
        if stripped.startswith(":try_start_"):
            return True
        if stripped.startswith(":try_end_") or stripped.startswith(".end method"):
            return False
    return False


def _insert_const_below_sget(content: str, flag: str) -> tuple[str, int, int]:
    lines = content.splitlines(True)
    output: list[str] = []
    insertions = 0
    skipped_unsafe = 0
    idx = 0
    while idx < len(lines):
        line = lines[idx]
        stripped = line.strip()
        if stripped.startswith("sget-boolean") and flag in stripped:
            register = _extract_register(stripped)
            if register and re.match(r"^[vp]\d+$", register):
                if _is_in_try_range(lines, idx):
                    output.append(line)
                    skipped_unsafe += 1
                    idx += 1
                    continue
                next_idx = idx + 1
                while next_idx < len(lines) and not lines[next_idx].strip():
                    next_idx += 1
                next_line = lines[next_idx].strip() if next_idx < len(lines) else ""
                if next_line != f"const/4 {register}, 0x1":
                    output.append(line)
                    indent = len(line) - len(line.lstrip())
                    output.append(" " * indent + f"const/4 {register}, 0x1\n")
                    insertions += 1
                    idx += 1
                    continue
        output.append(line)
        idx += 1
    return "".join(output), insertions, skipped_unsafe


def _patch_sysui_dir(unpacked_dir: Path) -> tuple[list[dict], list[str]]:
    results: list[dict] = []
    changed_classes: list[str] = []
    smali_dirs = _collect_smali_dirs(unpacked_dir)
    if not smali_dirs:
        results.append(_entry("MiuiSystemUI", str(unpacked_dir), found=True, status="skipped", detail="No smali dirs found in MiuiSystemUI unpacked dir"))
        return results, changed_classes

    for class_name in SYSUI_TARGET_CLASSES:
        smali_path = _find_smali_class(smali_dirs, class_name)
        if smali_path is None:
            results.append(_entry(class_name, f"{unpacked_dir}/**/{class_name}.smali", found=False, status="skipped", detail=f"{class_name}: class not found - skipped"))
            continue
        try:
            content = smali_path.read_text(encoding="utf-8", errors="ignore")
            patched, insertions, skipped_unsafe = _insert_const_below_sget(content, INTL_FLAG)
            if insertions:
                smali_path.write_text(patched, encoding="utf-8")
                changed_classes.append(class_name)
                results.append(_entry(class_name, str(smali_path), found=True, status="changed", detail=f"{class_name}: {insertions} const/4 inserted"))
            elif skipped_unsafe:
                results.append(_entry(class_name, str(smali_path), found=True, status="skipped", detail=f"{class_name}: all insertions skipped in try-range"))
            else:
                results.append(_entry(class_name, str(smali_path), found=True, status="skipped", detail=f"{class_name}: already patched or target flag not found"))
        except Exception as exc:
            results.append(_entry(class_name, str(smali_path), found=True, status="failed", error=str(exc)))
    return results, changed_classes


def _apkeditor_fallback(apk_path: Path) -> dict:
    apkeditor = rph.find_apkeditor()
    if apkeditor is None:
        return {"ok": False, "error": "APKEditor not found"}
    decoded_dir = Path(tempfile.mkdtemp(prefix="dz_sysui_ae_"))
    tmp_out = Path(tempfile.mktemp(suffix="_MiuiSystemUI.apk", dir=str(apk_path.parent)))
    try:
        decode = subprocess.run(["java", "-jar", str(apkeditor), "d", "-f", "-i", str(apk_path), "-o", str(decoded_dir)], capture_output=True, text=True, timeout=300)
        if decode.returncode != 0:
            return {"ok": False, "error": f"APKEditor decode rc={decode.returncode}: {decode.stderr[-300:]}"}
        _, _ = _patch_sysui_dir(decoded_dir)
        build = subprocess.run(["java", "-jar", str(apkeditor), "b", "-f", "-i", str(decoded_dir), "-o", str(tmp_out)], capture_output=True, text=True, timeout=300)
        if build.returncode != 0 or not tmp_out.is_file():
            tmp_out.unlink(missing_ok=True)
            return {"ok": False, "error": f"APKEditor build rc={build.returncode}: {build.stderr[-300:]}"}
        restore = rph.restore_patched_file_in_place(tmp_out, apk_path, "MiuiSystemUI.apk")
        return {"ok": restore["restored"], "error": restore.get("error")}
    finally:
        import shutil

        shutil.rmtree(decoded_dir, ignore_errors=True)


def apply_patch(work_dir: Path) -> dict:
    results: list[dict] = []
    rom_os = _detect_rom_os(work_dir)
    rom_region = _detect_rom_region(work_dir)

    if rom_os and rom_os not in ("OS2", "OS3"):
        results.append(_entry("MiuiSystemUI", str(work_dir), found=False, status="skipped", detail=f"ROM OS is {rom_os!r} - patch applies only to OS2/OS3", os_detection=rom_os))
        return _build_report(work_dir, results)
    if rom_region and rom_region != "CN":
        results.append(_entry("MiuiSystemUI", str(work_dir), found=False, status="skipped", detail=f"ROM region is {rom_region!r} - patch applies only to CN", os_detection=rom_os or "unknown"))
        return _build_report(work_dir, results)

    find_result = rph.find_miui_systemui_apk(work_dir)
    if not find_result["found"]:
        results.append(_entry("MiuiSystemUI", "MiuiSystemUI.apk", found=False, status="skipped_not_found", detail="MiuiSystemUI.apk not found", searched_paths=find_result["searched_paths"], os_detection=rom_os or "unknown"))
        return _build_report(work_dir, results)

    apk_path = Path(find_result["found_path"])
    unpacked_dir = Path(tempfile.mkdtemp(prefix="dz_sysui_unpacked_"))
    decompile = rph.decompile_apk(apk_path, unpacked_dir)
    if not decompile["ok"]:
        fallback = _apkeditor_fallback(apk_path)
        if fallback["ok"]:
            results.append(_entry("MiuiSystemUI", str(apk_path), found=True, status="changed", detail="MiuiSystemUI.apk patched and restored via APKEditor fallback", searched_paths=find_result["searched_paths"], os_detection=rom_os or "unknown"))
        else:
            results.append(_entry("MiuiSystemUI", str(apk_path), found=True, status="failed_optional", error=f"apktool decompile failed; APKEditor fallback failed: {fallback['error']}", searched_paths=find_result["searched_paths"], os_detection=rom_os or "unknown"))
        return _build_report(work_dir, results)

    try:
        patch_results, changed_classes = _patch_sysui_dir(unpacked_dir)
        results.extend(patch_results)
        rebuilt_apk = unpacked_dir.parent / "MiuiSystemUI_patched.apk"
        rebuild = rph.rebuild_apk(unpacked_dir, rebuilt_apk)
        if rebuild["ok"]:
            restore = rph.restore_patched_file_in_place(rebuilt_apk, apk_path, "MiuiSystemUI.apk")
            if restore["restored"]:
                results.append(_entry("MiuiSystemUI", str(apk_path), found=True, status="changed", detail="MiuiSystemUI.apk patched and restored in place", searched_paths=find_result["searched_paths"], os_detection=rom_os or "unknown"))
            else:
                results.append(_entry("MiuiSystemUI", str(apk_path), found=True, status="failed_optional", error=restore["error"], searched_paths=find_result["searched_paths"], os_detection=rom_os or "unknown"))
        else:
            smali_only_out = unpacked_dir.parent / "MiuiSystemUI_smali_only.apk"
            smali_rebuild = rph.rebuild_apk_smali_only(unpacked_dir, apk_path, smali_only_out)
            if smali_rebuild["ok"]:
                restore = rph.restore_patched_file_in_place(smali_only_out, apk_path, "MiuiSystemUI.apk")
                if restore["restored"]:
                    results.append(_entry("MiuiSystemUI", str(apk_path), found=True, status="changed", detail="MiuiSystemUI.apk patched and restored via smali-only fallback", searched_paths=find_result["searched_paths"], os_detection=rom_os or "unknown"))
                else:
                    results.append(_entry("MiuiSystemUI", str(apk_path), found=True, status="failed_optional", error=restore["error"], searched_paths=find_result["searched_paths"], os_detection=rom_os or "unknown"))
            else:
                fallback = _apkeditor_fallback(apk_path)
                if fallback["ok"]:
                    results.append(_entry("MiuiSystemUI", str(apk_path), found=True, status="changed", detail="MiuiSystemUI.apk patched and restored via APKEditor fallback", searched_paths=find_result["searched_paths"], os_detection=rom_os or "unknown"))
                else:
                    results.append(_entry("MiuiSystemUI", str(apk_path), found=True, status="failed_optional", error=f"apktool rebuild failed: {rebuild['reason']} | smali-only: {smali_rebuild['reason']} | apkeditor: {fallback['error']}", searched_paths=find_result["searched_paths"], os_detection=rom_os or "unknown"))
    finally:
        import shutil

        shutil.rmtree(unpacked_dir, ignore_errors=True)

    return _build_report(work_dir, results)


def _build_report(work_dir: Path, results: list[dict]) -> dict:
    skipped_statuses = {"skipped", "skipped_not_found"}
    failed_statuses = {"failed", "failed_optional"}
    summary = {
        "enabled": True,
        "total_scanned": len(results),
        "total_modified": sum(1 for result in results if result["status"] == "changed"),
        "total_skipped": sum(1 for result in results if result["status"] in skipped_statuses),
        "total_skipped_not_found": sum(1 for result in results if result["status"] == "skipped_not_found"),
        "total_failed": sum(1 for result in results if result["status"] in failed_statuses),
        "total_failed_optional": sum(1 for result in results if result["status"] == "failed_optional"),
        "results": results,
    }
    return {
        "generated": datetime.now(timezone.utc).isoformat(),
        "work_dir": str(work_dir),
        "patches": {PATCH_NAME: summary},
        "totals": {
            "total_scanned": summary["total_scanned"],
            "total_modified": summary["total_modified"],
            "total_skipped": summary["total_skipped"],
            "total_skipped_not_found": summary["total_skipped_not_found"],
            "total_failed": summary["total_failed"],
            "total_failed_optional": summary["total_failed_optional"],
        },
    }


def _write_reports(report: dict, reports_dir: Path) -> None:
    reports_dir.mkdir(parents=True, exist_ok=True)
    json_path = reports_dir / "systemui_hide_4g_show_volte_report.json"
    txt_path = reports_dir / "systemui_hide_4g_show_volte_report.txt"
    json_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    patch_data = report["patches"][PATCH_NAME]
    lines = [
        "=" * 72,
        "DeadZone MiuiSystemUI Hide 4G / Show VoLTE Report",
        f"Generated : {report['generated']}",
        f"Work dir  : {report['work_dir']}",
        "=" * 72,
        f"Scanned        : {patch_data['total_scanned']}",
        f"Modified       : {patch_data['total_modified']}",
        f"Skipped        : {patch_data['total_skipped']}",
        f"Skipped (NF)   : {patch_data['total_skipped_not_found']}",
        f"Failed         : {patch_data['total_failed']}",
        f"Failed (opt.)  : {patch_data['total_failed_optional']}",
        "",
    ]
    for result in patch_data["results"]:
        label = result.get("target_class") or result["target_file"]
        lines.append(f"[{result['status'].upper()}] {label}")
        if result.get("detail"):
            lines.append(f"  {result['detail']}")
        if result.get("error"):
            lines.append(f"  ERROR: {result['error']}")
    txt_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Patch MiuiSystemUI hide 4G / show VoLTE logic")
    parser.add_argument("--work-dir", default=str(WORK_DIR), help="Project root directory")
    parser.add_argument("--style", default="lite", help="Active build style")
    args = parser.parse_args(argv)

    work_dir = Path(args.work_dir).resolve()
    report = apply_patch(work_dir)
    _write_reports(report, work_dir / "bin" / "output" / "reports")
    failures = report["totals"]["total_failed"] - report["totals"]["total_failed_optional"]
    return 0 if failures == 0 else 2


if __name__ == "__main__":
    sys.exit(main())
