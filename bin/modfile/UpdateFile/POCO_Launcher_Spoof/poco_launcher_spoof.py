#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

WORK_DIR = Path(__file__).resolve().parents[4]
TARGET_KEY = "ro.product.vendor.brand"
TARGET_VALUE = "POCO"
REPLACE_WITH = "Redmi"
SCAN_DIRS = ("vendor", "odm")
EXTRA_BASES = ("build/baserom/images",)


def _parse_prop_line(line: str) -> tuple[str | None, str | None]:
    stripped = line.rstrip("\n\r")
    if stripped.startswith("#") or "=" not in stripped:
        return None, None
    key, _, value = stripped.partition("=")
    return key.strip(), value.strip()


def _replace_brand_in_file(prop_path: Path) -> dict:
    entry = {
        "target_file": str(prop_path),
        "found": False,
        "modified": False,
        "status": "skipped",
        "detail": "",
    }
    try:
        lines = prop_path.read_text(encoding="utf-8", errors="replace").splitlines(keepends=True)
    except OSError as exc:
        entry["status"] = "failed"
        entry["detail"] = str(exc)
        return entry

    new_lines: list[str] = []
    changed = False
    for line in lines:
        key, value = _parse_prop_line(line)
        if key == TARGET_KEY:
            entry["found"] = True
            if value == TARGET_VALUE:
                trail = line[len(line.rstrip("\n\r")) :]
                new_lines.append(f"{TARGET_KEY}={REPLACE_WITH}{trail}")
                changed = True
                continue
        new_lines.append(line)

    if changed:
        prop_path.write_text("".join(new_lines), encoding="utf-8")
        entry["modified"] = True
        entry["status"] = "changed"
        entry["detail"] = f"{TARGET_KEY} POCO -> Redmi"
    elif entry["found"]:
        entry["detail"] = f"{TARGET_KEY} found but value is not POCO"
    else:
        entry["detail"] = f"{TARGET_KEY} not present"
    return entry


def _candidate_partition_dirs(work_dir: Path) -> list[tuple[str, Path]]:
    seen: set[Path] = set()
    candidates: list[tuple[str, Path]] = []

    def add(label: str, path: Path) -> None:
        resolved = path.resolve()
        if resolved not in seen:
            seen.add(resolved)
            candidates.append((label, path))

    for base_rel in ("",) + EXTRA_BASES:
        base = work_dir / base_rel if base_rel else work_dir
        for part in SCAN_DIRS:
            add(part, base / part)
            add(f"{part}/{part}", base / part / part)
        add("odm/etc", base / "odm" / "etc")
    return candidates


def run_poco_spoof(work_dir: Path) -> dict:
    results: list[dict] = []
    poco_detected = False

    for partition, part_dir in _candidate_partition_dirs(work_dir):
        if not part_dir.is_dir():
            results.append(
                {
                    "target_file": str(part_dir),
                    "found": False,
                    "modified": False,
                    "status": "skipped",
                    "detail": f"{partition}/ not found",
                }
            )
            continue

        prop_files = sorted(part_dir.rglob("*.prop"))
        if not prop_files:
            results.append(
                {
                    "target_file": str(part_dir),
                    "found": False,
                    "modified": False,
                    "status": "skipped",
                    "detail": f"no *.prop files in {partition}/",
                }
            )
            continue

        for prop_file in prop_files:
            entry = _replace_brand_in_file(prop_file)
            results.append(entry)
            if entry["found"] and entry["modified"]:
                poco_detected = True

    any_found = any(result["found"] for result in results)
    overall_status = "changed" if poco_detected else ("skipped" if any_found else "skipped")
    return {
        "mod": "poco_launcher_to_miuihome_spoofing",
        "generated": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "work_dir": str(work_dir),
        "poco_rom": poco_detected,
        "overall_status": overall_status,
        "totals": {
            "scanned": sum(1 for result in results if result["status"] != "skipped" or result["found"]),
            "modified": sum(1 for result in results if result["modified"]),
            "skipped": sum(1 for result in results if result["status"] == "skipped"),
            "failed": sum(1 for result in results if result["status"] == "failed"),
        },
        "results": results,
    }


def _write_reports(report: dict, reports_dir: Path) -> None:
    reports_dir.mkdir(parents=True, exist_ok=True)
    json_path = reports_dir / "poco_launcher_spoof_report.json"
    json_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    lines = [
        "DeadZone MEZO - POCO Launcher to MiuiHome Spoofing Report",
        "=" * 55,
        f"Generated : {report['generated']}",
        f"Work dir  : {report['work_dir']}",
        f"POCO ROM  : {'YES' if report['poco_rom'] else 'NO'}",
        f"Status    : {report['overall_status'].upper()}",
        "",
        "Totals:",
        f"  Scanned : {report['totals']['scanned']}",
        f"  Modified: {report['totals']['modified']}",
        f"  Skipped : {report['totals']['skipped']}",
        f"  Failed  : {report['totals']['failed']}",
        "",
        "Results:",
    ]
    for result in report["results"]:
        tag = {"changed": "[CHANGED]", "skipped": "[SKIP   ]", "failed": "[FAILED ]"}.get(result["status"], "[UNKNOWN]")
        lines.append(f"  {tag} {Path(result['target_file']).name} - {result['detail']}")
    (reports_dir / "poco_launcher_spoof_report.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="POCO Launcher to MiuiHome Spoofing")
    parser.add_argument("--work-dir", default=str(WORK_DIR), help="Project root directory")
    parser.add_argument("--style", default="lite", help="Active build style")
    args = parser.parse_args(argv)

    enabled = os.environ.get("ENABLE_POCO_MIUIHOME_SPOOFING", "true").lower()
    if enabled not in ("1", "true", "yes"):
        print("[POCO_SPOOF] ENABLE_POCO_MIUIHOME_SPOOFING=false - skipped")
        return 0

    work_dir = Path(args.work_dir).resolve()
    report = run_poco_spoof(work_dir)
    _write_reports(report, work_dir / "bin" / "output" / "reports")
    if report["poco_rom"]:
        print(f"[POCO_SPOOF] POCO ROM detected - {TARGET_KEY} replaced with Redmi")
    else:
        print("[POCO_SPOOF] Not a POCO ROM or key not present - no changes made")
    return 0


if __name__ == "__main__":
    sys.exit(main())
