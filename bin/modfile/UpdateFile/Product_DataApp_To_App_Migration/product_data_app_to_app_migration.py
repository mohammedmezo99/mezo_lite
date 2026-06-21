#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import time
from pathlib import Path

WORK_DIR = Path(__file__).resolve().parents[4]
PRODUCT_BASES = ("build/baserom/images/product", "product")
SRC_SUBDIR = "data-app"
DST_SUBDIR = "app"


def _find_product_dir(work_dir: Path) -> Path | None:
    for rel in PRODUCT_BASES:
        candidate = work_dir / rel
        if candidate.is_dir():
            return candidate
    return None


def run_migration(work_dir: Path) -> dict:
    enabled = os.environ.get("ENABLE_PRODUCT_DATA_APP_MIGRATION", "true").lower()
    if enabled not in ("1", "true", "yes"):
        return {
            "mod": "product_data_app_to_app_migration",
            "generated": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "work_dir": str(work_dir),
            "overall_status": "disabled",
            "totals": {"moved": 0, "skipped": 0, "failed": 0},
            "results": [],
        }

    product_dir = _find_product_dir(work_dir)
    if product_dir is None:
        return {
            "mod": "product_data_app_to_app_migration",
            "generated": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "work_dir": str(work_dir),
            "overall_status": "skipped",
            "totals": {"moved": 0, "skipped": 0, "failed": 0},
            "results": [{"item": "product/", "status": "skipped", "detail": "product/ partition not found"}],
        }

    src_dir = product_dir / SRC_SUBDIR
    dst_dir = product_dir / DST_SUBDIR
    if not src_dir.is_dir():
        return {
            "mod": "product_data_app_to_app_migration",
            "generated": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "work_dir": str(work_dir),
            "overall_status": "skipped",
            "totals": {"moved": 0, "skipped": 0, "failed": 0},
            "results": [{"item": str(src_dir), "status": "skipped", "detail": "product/data-app/ not present - nothing to migrate"}],
        }

    dst_dir.mkdir(parents=True, exist_ok=True)
    items = sorted(src_dir.iterdir())
    if not items:
        return {
            "mod": "product_data_app_to_app_migration",
            "generated": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "work_dir": str(work_dir),
            "overall_status": "skipped",
            "totals": {"moved": 0, "skipped": 0, "failed": 0},
            "results": [{"item": str(src_dir), "status": "skipped", "detail": "product/data-app/ is empty"}],
        }

    results: list[dict] = []
    for item in items:
        dst_item = dst_dir / item.name
        entry = {"item": item.name, "src": str(item), "dst": str(dst_item)}
        if dst_item.exists():
            entry["status"] = "skipped"
            entry["detail"] = f"{item.name} already exists in product/app/ - not overwriting"
            results.append(entry)
            continue
        try:
            shutil.move(str(item), str(dst_item))
            entry["status"] = "moved"
            entry["detail"] = f"product/data-app/{item.name} -> product/app/{item.name}"
        except Exception as exc:
            entry["status"] = "failed"
            entry["detail"] = str(exc)
        results.append(entry)

    try:
        if src_dir.is_dir() and not any(src_dir.iterdir()):
            src_dir.rmdir()
    except Exception:
        pass

    moved = sum(1 for result in results if result["status"] == "moved")
    skipped = sum(1 for result in results if result["status"] == "skipped")
    failed = sum(1 for result in results if result["status"] == "failed")
    overall = "changed" if moved > 0 else ("failed" if failed > 0 else "skipped")
    return {
        "mod": "product_data_app_to_app_migration",
        "generated": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "work_dir": str(work_dir),
        "overall_status": overall,
        "totals": {"moved": moved, "skipped": skipped, "failed": failed},
        "results": results,
    }


def _write_reports(report: dict, reports_dir: Path) -> None:
    reports_dir.mkdir(parents=True, exist_ok=True)
    json_path = reports_dir / "product_data_app_migration_report.json"
    json_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    lines = [
        "DeadZone MEZO - product/data-app -> product/app Migration Report",
        "=" * 60,
        f"Generated : {report['generated']}",
        f"Work dir  : {report['work_dir']}",
        f"Status    : {report['overall_status'].upper()}",
        "",
        "Totals:",
        f"  Moved   : {report['totals']['moved']}",
        f"  Skipped : {report['totals']['skipped']}",
        f"  Failed  : {report['totals']['failed']}",
        "",
        "Results:",
    ]
    for result in report["results"]:
        tag = {"moved": "[MOVED  ]", "skipped": "[SKIP   ]", "failed": "[FAILED ]"}.get(result["status"], "[UNKNOWN]")
        lines.append(f"  {tag} {result['item']} - {result['detail']}")
    (reports_dir / "product_data_app_migration_report.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="product/data-app -> product/app migration")
    parser.add_argument("--work-dir", default=str(WORK_DIR), help="Project root directory")
    parser.add_argument("--style", default="lite", help="Active build style")
    args = parser.parse_args(argv)

    work_dir = Path(args.work_dir).resolve()
    report = run_migration(work_dir)
    _write_reports(report, work_dir / "bin" / "output" / "reports")
    if report["overall_status"] == "changed":
        print(f"[DATA_APP_MIGRATE] Migrated {report['totals']['moved']} item(s) from product/data-app/ to product/app/")
    elif report["overall_status"] == "disabled":
        print("[DATA_APP_MIGRATE] ENABLE_PRODUCT_DATA_APP_MIGRATION=false - skipped")
    else:
        print(f"[DATA_APP_MIGRATE] {report['overall_status'].upper()} - no items migrated")
    return 0 if report["totals"]["failed"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
