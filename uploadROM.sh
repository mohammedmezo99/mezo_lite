#!/bin/bash
set -euo pipefail

work_dir=$(pwd)
source "$work_dir/functions.sh"

version=$(< "$work_dir/Version")
raw_codename=$(< "$work_dir/bin/ddevice/device_code.txt")
rom_version=$(< "$work_dir/bin/ddevice/base_rom_code.txt")
android_version=$(< "$work_dir/bin/ddevice/androidver.txt")
region_type=$(< "$work_dir/bin/ddevice/device_type.txt")
baserom_type=$(< "$work_dir/bin/ddevice/romtype.txt")
device_f=$(< "$work_dir/bin/ddevice/device_f.txt")
super_img_path="$work_dir/build/baserom/images/super.img"
super_img_zst_path="$work_dir/build/baserom/images/super.img.zst"
final_root="$work_dir/out/final_package"

normalize_region() {
    case "${1,,}" in
        china) echo "ChinaStable" ;;
        global) echo "GlobalStable" ;;
        eeaglobal) echo "EeaStable" ;;
        inglobal) echo "IndiaStable" ;;
        idglobal) echo "IndonesiaStable" ;;
        ruglobal) echo "RussiaStable" ;;
        twglobal) echo "TaiwanStable" ;;
        trglobal) echo "TurkeyStable" ;;
        jpglobal) echo "JapanStable" ;;
        *) echo "$1" ;;
    esac
}

codename_upper=$(echo "$raw_codename" | tr '[:lower:]' '[:upper:]')
region_name=$(normalize_region "$region_type")
android_tag="A$(echo "$android_version" | tr -cd '0-9')"
final_name="DeadZoneLite_v${version}_${codename_upper}_${rom_version}_${region_name}-${android_tag}.zip"
output_file="$work_dir/out/$final_name"

if [[ "${1:-}" == "setup" ]]; then
    if [[ -z "${RCLONE_CONFIG_BASE64:-}" ]]; then
        echo "[ERROR] - Missing RCLONE_CONFIG_BASE64"
        exit 1
    fi

    printf '%s' "$RCLONE_CONFIG_BASE64" | base64 -d > "$work_dir/rclone.conf"
    chmod 600 "$work_dir/rclone.conf"
    exit 0
fi

if [[ ! -f "$super_img_path" ]]; then
    echo "[ERROR] - Missing super.img at build/baserom/images/super.img"
    exit 1
fi

mkdir -p "$work_dir/out"
rm -rf "$final_root"
rm -f "$output_file"
mkdir -p "$final_root/images"

upload "Compressing super.img"
zstd --rm -f "$super_img_path" -o "$super_img_zst_path" > /dev/null 2>&1
if [[ ! -f "$super_img_zst_path" ]]; then
    echo "[ERROR] - Failed to create super.img.zst"
    exit 1
fi

case "$baserom_type" in
    payload)
        cp -f "$super_img_zst_path" "$final_root/"
        find "$work_dir/build/baserom/images" -maxdepth 1 -type f -name "*.img" -exec cp -f {} "$final_root/images/" \;
        ;;
    br)
        if [[ ! -d "$work_dir/build/baserom/firmware-update" ]]; then
            echo "[ERROR] - Missing firmware-update directory for br ROM packaging"
            exit 1
        fi
        cp -f "$super_img_zst_path" "$final_root/"
        find "$work_dir/build/baserom/firmware-update" -maxdepth 1 -type f -exec cp -f {} "$final_root/images/" \;
        ;;
    *)
        echo "[ERROR] - Unsupported rom type: $baserom_type"
        exit 1
        ;;
esac

cp -rf "$work_dir/bin/script2flash/META-INF" "$final_root/"
cp -f "$work_dir/bin/script2flash/"*.bat "$final_root/" 2>/dev/null || true
cp -f "$work_dir/bin/script2flash/"*.sh "$final_root/" 2>/dev/null || true

if [[ -f "$work_dir/bin/script2flash/cust.img" ]]; then
    cp -f "$work_dir/bin/script2flash/cust.img" "$final_root/images/"
fi

printf '%s\n' "$device_f" > "$final_root/META-INF/Data/DeviceCode"
printf '%s\n' "$region_type" > "$final_root/META-INF/Data/Region"

if [[ ! -s "$final_root/META-INF/Data/DeviceCode" ]]; then
    echo "[ERROR] - META-INF/Data/DeviceCode is empty"
    exit 1
fi

find "$final_root" -exec touch -t 200901010000.00 {} + 2>/dev/null || true
(
    cd "$final_root"
    zip -qr "$output_file" ./*
)

if [[ ! -f "$output_file" ]]; then
    echo "[ERROR] - Final ZIP was not created"
    exit 1
fi

zip_listing=$(unzip -Z1 "$output_file")
if printf '%s\n' "$zip_listing" | grep -Eq '(^package/|^final_package/|(^|/)package\.zip$)'; then
    echo "[ERROR] - Final ZIP contains an unexpected parent folder or stale package.zip"
    exit 1
fi

if ! printf '%s\n' "$zip_listing" | grep -qx 'META-INF/'; then
    echo "[ERROR] - Final ZIP is missing META-INF/ at the archive root"
    exit 1
fi
if ! printf '%s\n' "$zip_listing" | grep -qx 'super.img.zst'; then
    echo "[ERROR] - Final ZIP is missing super.img.zst at the archive root"
    exit 1
fi
if ! printf '%s\n' "$zip_listing" | grep -q '^images/'; then
    echo "[ERROR] - Final ZIP is missing images/ content"
    exit 1
fi
if ! printf '%s\n' "$zip_listing" | grep -qx 'Windows_FastbootInstall.bat'; then
    echo "[ERROR] - Final ZIP is missing Windows_FastbootInstall.bat"
    exit 1
fi

echo "$final_name" > "$work_dir/bin/ddevice/output_zip.txt"

if [[ "${DEADZONE_DRY_RUN:-0}" == "1" ]]; then
    upload "Dry-run packaging complete"
    exit 0
fi

remote_name="${RCLONE_REMOTE_NAME:-gdrive}"
remote_dir="${RCLONE_UPLOAD_DIR:-}"
if [[ -z "$remote_dir" ]]; then
    echo "[ERROR] - Missing RCLONE_UPLOAD_DIR"
    exit 1
fi

remote_path="${remote_name}:${remote_dir}"
upload "Uploading DeadZone Lite to Google Drive"
rclone --config="$work_dir/rclone.conf" copyto "$output_file" "${remote_path}/${final_name}" > /dev/null 2>&1

drive_link=$(rclone --config="$work_dir/rclone.conf" link "${remote_path}/${final_name}" 2>/dev/null | tail -n 1 | tr -d '\r')
if [[ -z "$drive_link" ]]; then
    echo "[ERROR] - Public Google Drive link could not be created"
    exit 1
fi

echo "$drive_link" > "$work_dir/bin/ddevice/drive_link.txt"

upload "Cleaning workspace"
rm -rf "$work_dir/build"
