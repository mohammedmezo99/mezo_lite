#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import rom_patch_helpers as rph

WORK_DIR = Path(__file__).resolve().parents[4]
PATCH_NAME = "provisions_deadzone_branding"
TARGET_STRINGS = {
    "miui14_global_start_up_slogan": "Lets rock with MEZO Development Project",
    "miui14_start_up_slogan": "Lets rock with MEZO Development Project",
    "provision_complete_text": "Ready to Rock with DeadZoneROM!",
}


def _entry(target_file: str, *, found: bool, status: str, detail: str = "", error: str | None = None, searched_paths: list[str] | None = None) -> dict:
    return {
        "patch_name": PATCH_NAME,
        "target_file": target_file,
        "found": found,
        "status": status,
        "detail": detail,
        "error": error,
        "searched_paths": searched_paths or [],
    }


def _patch_strings_xml(xml_path: Path, strings: dict[str, str]) -> tuple[bool, dict[str, str]]:
    import re

    content = xml_path.read_text(encoding="utf-8", errors="ignore")
    original = content
    results: dict[str, str] = {}
    for name, value in strings.items():
        pattern = rf'(<string\s+name="{re.escape(name)}"[^>]*>)(.*?)(</string>)'
        match = re.search(pattern, content, re.DOTALL)
        if match:
            if match.group(2) != value:
                content = content[: match.start(2)] + value + content[match.end(2) :]
                results[name] = "updated"
            else:
                results[name] = "unchanged"
        else:
            results[name] = "missing"
    if content != original:
        xml_path.write_text(content, encoding="utf-8")
        return True, results
    return False, results


def _add_missing_strings(xml_path: Path, strings: dict[str, str]) -> None:
    import re

    content = xml_path.read_text(encoding="utf-8", errors="ignore")
    new_lines = "\n".join(f'    <string name="{name}">{value}</string>' for name, value in strings.items())
    updated, count = re.subn(r"(</resources>)", new_lines + "\n" + r"\1", content, count=1)
    if count:
        xml_path.write_text(updated, encoding="utf-8")
        return
    xml_path.write_text(content.rstrip() + "\n" + new_lines + "\n</resources>\n", encoding="utf-8")


def _patch_provision_dir(unpacked_dir: Path) -> list[dict]:
    results: list[dict] = []
    xml_files = sorted(unpacked_dir.glob("res/values*/strings.xml"))
    if not xml_files:
        results.append(_entry(str(unpacked_dir / "res/values/strings.xml"), found=False, status="skipped", detail="No res/values*/strings.xml found in provision dir"))
        return results

    found_in: dict[str, list[Path]] = {name: [] for name in TARGET_STRINGS}
    for xml_path in xml_files:
        content = xml_path.read_text(encoding="utf-8", errors="ignore")
        for name in TARGET_STRINGS:
            if f'name="{name}"' in content:
                found_in[name].append(xml_path)

    for xml_path in xml_files:
        scoped_strings = {name: value for name, value in TARGET_STRINGS.items() if xml_path in found_in[name]}
        if not scoped_strings:
            continue
        try:
            changed, status_map = _patch_strings_xml(xml_path, scoped_strings)
            updated = [name for name, state in status_map.items() if state == "updated"]
            unchanged = [name for name, state in status_map.items() if state == "unchanged"]
            if changed:
                results.append(_entry(str(xml_path), found=True, status="changed", detail=f"Updated: {updated}; unchanged: {unchanged}"))
            else:
                results.append(_entry(str(xml_path), found=True, status="skipped", detail=f"All strings already correct: {unchanged}"))
        except Exception as exc:
            results.append(_entry(str(xml_path), found=True, status="failed", error=str(exc)))

    missing = {name: value for name, value in TARGET_STRINGS.items() if not found_in[name]}
    if missing:
        base_strings = unpacked_dir / "res" / "values" / "strings.xml"
        if not base_strings.exists():
            base_strings.parent.mkdir(parents=True, exist_ok=True)
            base_strings.write_text('<?xml version="1.0" encoding="utf-8"?>\n<resources>\n</resources>\n', encoding="utf-8")
        try:
            _add_missing_strings(base_strings, missing)
            results.append(_entry(str(base_strings), found=True, status="changed", detail=f"Added missing strings: {list(missing)}"))
        except Exception as exc:
            results.append(_entry(str(base_strings), found=True, status="failed", error=str(exc)))
    return results


def _restore_temp_apk(tmp_out: Path, original_apk: Path) -> dict:
    restore = rph.restore_patched_file_in_place(tmp_out, original_apk, original_apk.name)
    return {"ok": restore["restored"], "restored_path": restore.get("restored_path"), "rebuilt_path": restore.get("rebuilt_path"), "permission": restore.get("permission"), "error": restore.get("error")}


def _apkeditor_fallback(apk_path: Path) -> dict:
    apkeditor = rph.find_apkeditor()
    if apkeditor is None:
        return {"ok": False, "error": "APKEditor not found"}

    decoded_dir = Path(tempfile.mkdtemp(prefix="dz_provision_ae_"))
    tmp_out = Path(tempfile.mktemp(suffix="_Provision.apk", dir=str(apk_path.parent)))
    try:
        decode = subprocess.run(["java", "-jar", str(apkeditor), "d", "-f", "-i", str(apk_path), "-o", str(decoded_dir)], capture_output=True, text=True, timeout=300)
        if decode.returncode != 0:
            return {"ok": False, "error": f"APKEditor decode rc={decode.returncode}: {decode.stderr[-300:]}"}
        _patch_provision_dir(decoded_dir)
        build = subprocess.run(["java", "-jar", str(apkeditor), "b", "-f", "-i", str(decoded_dir), "-o", str(tmp_out)], capture_output=True, text=True, timeout=300)
        if build.returncode != 0 or not tmp_out.is_file():
            tmp_out.unlink(missing_ok=True)
            return {"ok": False, "error": f"APKEditor build rc={build.returncode}: {build.stderr[-300:]}"}
        restored = _restore_temp_apk(tmp_out, apk_path)
        return {"ok": restored["ok"], "rebuilt_path": restored.get("rebuilt_path"), "restored_path": restored.get("restored_path"), "permission": restored.get("permission"), "error": restored.get("error")}
    finally:
        import shutil

        shutil.rmtree(decoded_dir, ignore_errors=True)


def apply_patch(work_dir: Path) -> dict:
    find_result = rph.find_provision_apk(work_dir)
    results: list[dict] = []
    if not find_result["found"]:
        results.append(_entry("Provision.apk", found=False, status="skipped_not_found", detail="Provision.apk not found", searched_paths=find_result["searched_paths"]))
        return _build_report(work_dir, results)

    apk_path = Path(find_result["found_path"])
    unpacked_dir = Path(tempfile.mkdtemp(prefix="dz_provision_unpacked_"))
    decompile = rph.decompile_apk(apk_path, unpacked_dir)
    if not decompile["ok"]:
        fallback = _apkeditor_fallback(apk_path)
        if fallback["ok"]:
            results.append(_entry(str(apk_path), found=True, status="changed", detail="Provision.apk patched and restored via APKEditor fallback", searched_paths=find_result["searched_paths"]))
        else:
            results.append(_entry(str(apk_path), found=True, status="failed_optional", error=f"apktool decompile failed; APKEditor fallback failed: {fallback['error']}", searched_paths=find_result["searched_paths"]))
        return _build_report(work_dir, results)

    try:
        results.extend(_patch_provision_dir(unpacked_dir))
        rebuilt_apk = unpacked_dir.parent / "Provision_patched.apk"
        rebuild = rph.rebuild_apk(unpacked_dir, rebuilt_apk)
        if rebuild["ok"]:
            restore = rph.restore_patched_file_in_place(rebuilt_apk, apk_path, "Provision.apk")
            if restore["restored"]:
                results.append(_entry(str(apk_path), found=True, status="changed", detail="Provision.apk patched and restored in place", searched_paths=find_result["searched_paths"]))
            else:
                results.append(_entry(str(apk_path), found=True, status="failed_optional", error=restore["error"], searched_paths=find_result["searched_paths"]))
        else:
            fallback = _apkeditor_fallback(apk_path)
            if fallback["ok"]:
                results.append(_entry(str(apk_path), found=True, status="changed", detail="Provision.apk patched and restored via APKEditor fallback", searched_paths=find_result["searched_paths"]))
            else:
                results.append(_entry(str(apk_path), found=True, status="failed_optional", error=f"apktool rebuild failed: {rebuild['reason']} | apkeditor: {fallback['error']}", searched_paths=find_result["searched_paths"]))
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
    json_path = reports_dir / "provisions_deadzone_branding_report.json"
    txt_path = reports_dir / "provisions_deadzone_branding_report.txt"
    json_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    patch_data = report["patches"][PATCH_NAME]
    lines = [
        "=" * 72,
        "DeadZone Provision Branding Report",
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
        lines.append(f"[{result['status'].upper()}] {result['target_file']}")
        if result.get("detail"):
            lines.append(f"  {result['detail']}")
        if result.get("error"):
            lines.append(f"  ERROR: {result['error']}")
    txt_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Patch Provision.apk branding strings")
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
