import html
import os
import re
import sys
from datetime import datetime
from pathlib import Path

import requests


ROOT = Path(__file__).resolve().parent
TIMEOUT = 30
RELEASE_IMAGE = ROOT / "assets" / "release" / "lite.png"

PRIVATE_STAGE_MESSAGES = {
    "request_received": "DeadZone Lite build request received",
    "build_started": "Build started",
    "packaging_started": "Packaging started",
    "upload_started": "Upload started to Google Drive",
    "success": "Build completed successfully",
    "fail": "Build failed",
    "publish_prompt": "Publish decision required",
}

REGION_MAP = {
    "china": "ChinaStable",
    "global": "GlobalStable",
    "eeaglobal": "EEAStable",
    "europe": "EEAStable",
    "inglobal": "IndiaStable",
    "indiaglobal": "IndiaStable",
    "idglobal": "IndonesiaStable",
    "indonesiaglobal": "IndonesiaStable",
    "ruglobal": "RussiaStable",
    "russiaglobal": "RussiaStable",
    "twglobal": "TaiwanStable",
    "taiwanglobal": "TaiwanStable",
    "trglobal": "TurkeyStable",
    "turkeyglobal": "TurkeyStable",
    "jpglobal": "JapanStable",
    "japanglobal": "JapanStable",
}

REGION_BASE_TEXT = {
    "GlobalStable": "Based on pure Global ROM",
    "ChinaStable": "Based on pure China ROM",
    "IndiaStable": "Based on pure Indian ROM",
    "IndonesiaStable": "Based on pure Indonesian ROM",
    "EEAStable": "Based on pure EEA ROM",
    "RussiaStable": "Based on pure Russia ROM",
    "TurkeyStable": "Based on pure Turkey ROM",
    "TaiwanStable": "Based on pure Taiwan ROM",
    "JapanStable": "Based on pure Japan ROM",
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
    key = re.sub(r"[^a-z]", "", (region_value or "").strip().lower())
    return REGION_MAP.get(key, region_value or "Unknown")


def clean_codename(raw_codename: str) -> str:
    value = (raw_codename or "").strip().lower()
    if "|" in value:
        value = value.split("|", 1)[0].strip()
    value = re.sub(r"[_-]+", "", value)
    for suffix in (
        "globalstable",
        "chinastable",
        "indiastable",
        "indonesiastable",
        "eeastable",
        "europestable",
        "russiastable",
        "turkeystable",
        "taiwanstable",
        "japanstable",
        "global",
        "china",
        "india",
        "indonesia",
        "eea",
        "europe",
        "russia",
        "turkey",
        "taiwan",
        "japan",
        "stable",
    ):
        if value.endswith(suffix):
            value = value[: -len(suffix)]
            break
    value = re.sub(r"[^a-z0-9]+", "", value)
    return value or "unknown"


def normalize_codename(raw_codename: str) -> str:
    return clean_codename(raw_codename).upper()


def clean_device_name(raw_name: str) -> str:
    parts = [part.strip() for part in (raw_name or "").split("|") if part.strip()]
    unique_parts: list[str] = []
    for part in parts:
        if part not in unique_parts:
            unique_parts.append(part)
    if not unique_parts:
        return "Unknown Xiaomi Device"
    five_g = [part for part in unique_parts if "5G" in part]
    candidates = five_g or unique_parts
    return max(candidates, key=lambda item: (len(item), item))


def build_output_filename(version: str, codename: str, rom_version: str, region: str, android_tag: str) -> str:
    safe_version = (version or "0.00").strip()
    safe_rom_version = (rom_version or "Unknown").strip()
    safe_region = (region or "Unknown").strip()
    safe_android = (android_tag or "Unknown").strip()
    return f"DeadZoneLite_v{safe_version}_{codename}_{safe_rom_version}_{safe_region}-{safe_android}.zip"


def derive_platform(rom_version: str) -> str:
    match = re.match(r"^(OS\d+\.\d+)", (rom_version or "").strip())
    return match.group(1) if match else "Unknown"


def derive_hyperos_major(rom_version: str) -> str:
    match = re.match(r"^OS(\d+)", (rom_version or "").strip())
    return f"HyperOS {match.group(1)}" if match else "HyperOS"


def derive_os_tag(rom_version: str) -> str:
    match = re.match(r"^OS(\d+)", (rom_version or "").strip())
    return f"OS{match.group(1)}" if match else "OS"


def derive_hyperos_tag(rom_version: str) -> str:
    match = re.match(r"^OS(\d+)", (rom_version or "").strip())
    return f"HyperOS{match.group(1)}" if match else "HyperOS"


def derive_android_hash_tag(android_tag: str) -> str:
    digits = re.sub(r"[^0-9]", "", android_tag or "")
    return f"Android{digits}" if digits else "Android"


def safe_link(value: str) -> str:
    return html.escape((value or "").strip(), quote=True)


def get_metadata() -> dict:
    version = read_text("Version", "0.00")
    codename_raw = read_text("bin/ddevice/codename.txt") or read_text("bin/ddevice/device_code.txt")
    codename = normalize_codename(codename_raw)
    rom_version = read_text("bin/ddevice/rom_version.txt") or read_text("bin/ddevice/base_rom_code.txt", "Unknown")
    region = normalize_region(read_text("bin/ddevice/region.txt") or read_text("bin/ddevice/device_type.txt", "Unknown"))
    android = normalize_android(read_text("bin/ddevice/android_version.txt") or read_text("bin/ddevice/androidver.txt", ""))
    platform = read_text("bin/ddevice/platform.txt") or derive_platform(rom_version)
    device_name = clean_device_name(read_text("bin/ddevice/device_name.txt") or read_text("bin/ddevice/name_devices.txt", "Unknown Xiaomi Device"))
    filename = read_text("bin/ddevice/output_zip.txt")
    if not filename:
        filename = build_output_filename(version, codename, rom_version, region, android)
    return {
        "version": version,
        "codename": codename,
        "codename_lower": codename.lower(),
        "rom_version": rom_version,
        "region": region,
        "android": android,
        "android_number": re.sub(r"[^0-9]", "", android),
        "platform": platform,
        "hyperos_major": derive_hyperos_major(rom_version),
        "os_tag": derive_os_tag(rom_version),
        "hyperos_tag": derive_hyperos_tag(rom_version),
        "android_hash_tag": derive_android_hash_tag(android),
        "device_name": device_name or "Unknown Xiaomi Device",
        "filename": filename,
        "drive_link": read_text("bin/ddevice/drive_link.txt"),
        "date": datetime.now().strftime("%d/%m/%Y"),
        "region_base_text": REGION_BASE_TEXT.get(region, "Based on pure official ROM"),
    }


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
        "release_post": "release notification",
        "release_notification": "release notification",
    }
    return mapping.get((stage or "").strip(), stage or "unknown")


def format_private_message(status: str, stage: str = "") -> str:
    metadata = get_metadata()
    header = PRIVATE_STAGE_MESSAGES.get(status, "Status update")
    details = []
    request_source = (os.environ.get("REQUEST_SOURCE") or "").strip().lower()

    if status == "request_received":
        if request_source.startswith("telegram"):
            details.append("DeadZone Lite request received from Telegram.")
        else:
            details.append("Manual GitHub build request received.")
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
    elif status == "publish_prompt":
        details.append("Manual GitHub build completed.")
        details.append("This build was uploaded but not posted publicly.")
        details.append(f"File: {metadata['filename']}")
        details.append(f"Device: {metadata['codename']}")
        details.append(f"ROM Version: {metadata['rom_version']}")
        details.append(f"Region: {metadata['region']}")
        details.append(f"Android: {metadata['android']}")
        if metadata["drive_link"]:
            details.append(f"Drive Link: {metadata['drive_link']}")
        details.append("Publish to release channel? Yes / No")
    elif status == "fail":
        failure_stage = stage or os.environ.get("CURRENT_STAGE", "unknown")
        details.append(f"Stage: {humanize_stage(failure_stage)}")
        details.append("Please check the build environment.")

    return "\n".join([header, *details])


def format_release_caption() -> str:
    metadata = get_metadata()
    drive_link = metadata["drive_link"].strip()
    if not drive_link:
        raise RuntimeError("Missing Google Drive link")

    mezo_contact_link = safe_link(os.environ.get("MEZO_CONTACT_LINK", ""))
    discussion_link = safe_link(os.environ.get("CHAT_GROUP_LINK", ""))
    changelog_link = safe_link(os.environ.get("CHANGELOG_LINK") or os.environ.get("UPDATES_GROUP_LINK", ""))
    screenshots_link = safe_link(os.environ.get("SCREENSHOTS_POST_LINK") or os.environ.get("SCREENSHOTS_GROUP_LINK", ""))
    download_link = safe_link(drive_link)

    return (
        f"<b>DeadZone Lite v{html.escape(metadata['version'])}</b>\n\n"
        f"<b>{html.escape(metadata['hyperos_major'])}</b> • <b>{html.escape(metadata['rom_version'])}</b>\n"
        f"<b>{html.escape(metadata['region'])}</b> • <b>{html.escape(metadata['android'])}</b> • <b>{html.escape(metadata['platform'])}</b>\n\n"
        f"<b>Device</b>\n{html.escape(metadata['device_name'])}\n\n"
        f"<b>Code Name</b>\n#{html.escape(metadata['codename_lower'])}\n\n"
        f"<b>Release Date</b>\n{html.escape(metadata['date'])}\n\n"
        f"<b>Base</b>\n{html.escape(metadata['region_base_text'])}\n\n"
        f"<b>Developer</b> <a href=\"{mezo_contact_link}\">MEZO</a>\n\n"
        f"<b>Changelog</b> <a href=\"{changelog_link}\">Here</a>\n"
        f"<b>Download</b> <a href=\"{download_link}\">Here</a>\n"
        f"<b>Screenshots</b> <a href=\"{screenshots_link}\">Here</a>\n"
        f"<b>Discussion</b> <a href=\"{discussion_link}\">Here</a>\n\n"
        f"#{html.escape(metadata['codename_lower'])} "
        f"#{html.escape(metadata['os_tag'])} "
        f"#{html.escape(metadata['hyperos_tag'])} "
        f"#{html.escape(metadata['android_hash_tag'])} "
        f"#DeadZone #DeadZoneLite #MEZO"
    )


def send_telegram_message(chat_id: str, text: str, parse_mode: str | None = None) -> None:
    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not bot_token:
        raise RuntimeError("Missing TELEGRAM_BOT_TOKEN")
    payload = {
        "chat_id": chat_id,
        "text": text,
        "disable_web_page_preview": True,
    }
    if parse_mode:
        payload["parse_mode"] = parse_mode
    response = requests.post(
        f"https://api.telegram.org/bot{bot_token}/sendMessage",
        json=payload,
        timeout=TIMEOUT,
    )
    response.raise_for_status()


def send_telegram_photo(chat_id: str, caption: str, image_path: Path) -> None:
    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not bot_token:
        raise RuntimeError("Missing TELEGRAM_BOT_TOKEN")
    with image_path.open("rb") as image_file:
        response = requests.post(
            f"https://api.telegram.org/bot{bot_token}/sendPhoto",
            data={
                "chat_id": chat_id,
                "caption": caption,
                "parse_mode": "HTML",
                "disable_web_page_preview": "true",
            },
            files={"photo": image_file},
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
    caption = format_release_caption()
    if RELEASE_IMAGE.is_file():
        try:
            send_telegram_photo(chat_id, caption, RELEASE_IMAGE)
            return
        except Exception:
            send_telegram_message(chat_id, caption, parse_mode="HTML")
            return
    send_telegram_message(chat_id, caption, parse_mode="HTML")


def usage() -> str:
    return (
        "Usage:\n"
        "  python notify.py private <request_received|build_started|packaging_started|upload_started|success|fail> [stage]\n"
        "  python notify.py private publish_prompt\n"
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
