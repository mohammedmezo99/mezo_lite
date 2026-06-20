import os
import re
import sys
from pathlib import Path

import requests


ROOT = Path(__file__).resolve().parent
TIMEOUT = 30

PRIVATE_STAGE_MESSAGES = {
    "request_received": "📥 New DeadZone Lite build request received",
    "build_started": "🛠️ Build started",
    "packaging_started": "📦 Packaging started",
    "upload_started": "☁️ Upload started to Google Drive",
    "success": "✅ Build completed successfully",
    "fail": "❌ Build failed",
}


def read_text(relative_path: str, default: str = "") -> str:
    path = ROOT / relative_path
    if not path.exists():
        return default
    try:
        return path.read_text(encoding="utf-8").strip() or default
    except Exception:
        return default


def write_github_env(name: str, value: str) -> None:
    github_env = os.environ.get("GITHUB_ENV")
    if not github_env or value is None:
        return
    with open(github_env, "a", encoding="utf-8") as handle:
        handle.write(f"{name}={value}\n")


def normalize_android(android_value: str) -> str:
    digits = re.sub(r"[^0-9]", "", android_value or "")
    return f"A{digits}" if digits else "Unknown"


def normalize_region(region_value: str) -> str:
    region_map = {
        "china": "ChinaStable",
        "global": "GlobalStable",
        "eeaglobal": "EeaStable",
        "europe": "EeaStable",
        "inglobal": "IndiaStable",
        "indiaglobal": "IndiaStable",
        "idglobal": "IdStable",
        "ruglobal": "RuStable",
        "twglobal": "TwStable",
        "trglobal": "TrStable",
        "jpglobal": "JpStable",
    }
    key = re.sub(r"[^a-z]", "", (region_value or "").strip().lower())
    return region_map.get(key, region_value or "Unknown")


def normalize_codename(raw_codename: str) -> str:
    return re.sub(r"[^A-Za-z0-9_]+", "", (raw_codename or "").strip()).upper() or "UNKNOWN"


def build_output_filename(version: str, codename: str, rom_version: str, region: str, android_tag: str) -> str:
    safe_version = (version or "0.00").strip()
    safe_rom_version = (rom_version or "Unknown").strip()
    safe_region = (region or "Unknown").strip()
    safe_android = (android_tag or "Unknown").strip()
    return f"DeadZoneLite_v{safe_version}_{codename}_{safe_rom_version}_{safe_region}-{safe_android}.zip"


def get_metadata() -> dict:
    version = read_text("Version", "0.00")
    codename = normalize_codename(read_text("bin/ddevice/device_code.txt"))
    rom_version = read_text("bin/ddevice/base_rom_code.txt", "Unknown")
    region = normalize_region(read_text("bin/ddevice/device_type.txt", "Unknown"))
    android = normalize_android(read_text("bin/ddevice/androidver.txt", ""))
    filename = read_text("bin/ddevice/output_zip.txt")
    if not filename:
        filename = build_output_filename(version, codename, rom_version, region, android)
    return {
        "version": version,
        "codename": codename,
        "rom_version": rom_version,
        "region": region,
        "android": android,
        "filename": filename,
        "drive_link": read_text("bin/ddevice/drive_link.txt"),
    }


def format_private_message(status: str, stage: str = "") -> str:
    metadata = get_metadata()
    header = PRIVATE_STAGE_MESSAGES.get(status, "ℹ️ Status update")
    details = []

    if status == "request_received":
        details.append("DeadZone Lite request has been accepted from the public group.")
    elif status == "build_started":
        details.append(
            f"Build started for {metadata['codename']} | {metadata['rom_version']} | {metadata['region']} | {metadata['android']}"
        )
    elif status == "packaging_started":
        details.append(f"Packaging started for {metadata['filename']}")
    elif status == "upload_started":
        details.append(f"Preparing to upload {metadata['filename']}")
    elif status == "success":
        details.append(f"File: {metadata['filename']}")
        details.append(f"Device: {metadata['codename']}")
        details.append(f"ROM Version: {metadata['rom_version']}")
        details.append(f"Region: {metadata['region']}")
        details.append(f"Android: {metadata['android']}")
        if metadata["drive_link"]:
            details.append(f"Drive Link: {metadata['drive_link']}")
    elif status == "fail":
        failure_stage = stage or os.environ.get("CURRENT_STAGE", "unknown")
        details.append(f"Stage: {humanize_stage(failure_stage)}")
        details.append("Please check the build environment.")

    return "\n".join([header, *details])


def format_release_post() -> str:
    metadata = get_metadata()
    return (
        "🎉 DeadZone Lite Build Completed\n\n"
        f"📦 File:\n{metadata['filename']}\n\n"
        f"📱 Device: {metadata['codename']}\n"
        f"🧩 ROM Version: {metadata['rom_version']}\n"
        f"🌍 Region: {metadata['region']}\n"
        f"🤖 Android: {metadata['android']}\n\n"
        f"☁️ Download:\n{metadata['drive_link']}\n\n"
        "✨ Powered by DeadZone Lite"
    )


def humanize_stage(stage: str) -> str:
    mapping = {
        "checkout": "checkout",
        "request_acknowledged": "request acknowledgement",
        "install_dependencies": "dependency installation",
        "parse_rom_metadata": "ROM metadata parsing",
        "build": "build",
        "package": "packaging",
        "setup_rclone": "rclone setup",
        "upload_drive": "Google Drive upload",
        "release_post": "release posting",
    }
    return mapping.get((stage or "").strip(), stage or "unknown")


def send_telegram_message(chat_id: str, text: str) -> None:
    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not bot_token:
        raise RuntimeError("Missing TELEGRAM_BOT_TOKEN")
    response = requests.post(
        f"https://api.telegram.org/bot{bot_token}/sendMessage",
        json={
            "chat_id": chat_id,
            "text": text,
            "disable_web_page_preview": True,
        },
        timeout=TIMEOUT,
    )
    response.raise_for_status()


def handle_private(status: str, stage: str = "") -> None:
    chat_id = os.environ.get("MEZO_PRIVATE_CHAT_ID")
    if not chat_id:
        raise RuntimeError("Missing MEZO_PRIVATE_CHAT_ID")
    send_telegram_message(chat_id, format_private_message(status, stage))


def handle_release() -> None:
    chat_id = os.environ.get("TELEGRAM_RELEASE_GROUP_ID")
    if not chat_id:
        raise RuntimeError("Missing TELEGRAM_RELEASE_GROUP_ID")
    send_telegram_message(chat_id, format_release_post())


def usage() -> str:
    return (
        "Usage:\n"
        "  python notify.py private <request_received|build_started|packaging_started|upload_started|success|fail> [stage]\n"
        "  python notify.py release success\n"
        "  python notify.py filename"
    )


def main() -> int:
    if len(sys.argv) < 2:
        print(usage())
        return 1

    mode = sys.argv[1].strip().lower()

    if mode == "private":
        if len(sys.argv) < 3:
            print(usage())
            return 1
        status = sys.argv[2].strip().lower()
        stage = sys.argv[3].strip() if len(sys.argv) > 3 else ""
        handle_private(status, stage)
        return 0

    if mode == "release":
        if len(sys.argv) < 3 or sys.argv[2].strip().lower() != "success":
            print(usage())
            return 1
        handle_release()
        return 0

    if mode == "filename":
        metadata = get_metadata()
        print(metadata["filename"])
        write_github_env("FINAL_ROM_FILENAME", metadata["filename"])
        return 0

    print(usage())
    return 1


if __name__ == "__main__":
    sys.exit(main())
