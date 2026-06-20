#!/bin/bash
set -euo pipefail

work_dir=$(pwd)
source "$work_dir/functions.sh"

version=$(< "$work_dir/Version")
raw_codename=$(< "$work_dir/bin/ddevice/device_code.txt")
rom_version=$(< "$work_dir/bin/ddevice/base_rom_code.txt")
android_version=$(< "$work_dir/bin/ddevice/androidver.txt")
region_type=$(< "$work_dir/bin/ddevice/device_type.txt")

normalize_region() {
    case "${1,,}" in
        china) echo "ChinaStable" ;;
        global) echo "GlobalStable" ;;
        eeaglobal) echo "EeaStable" ;;
        inglobal) echo "IndiaStable" ;;
        idglobal) echo "IdStable" ;;
        ruglobal) echo "RuStable" ;;
        twglobal) echo "TwStable" ;;
        trglobal) echo "TrStable" ;;
        jpglobal) echo "JpStable" ;;
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

source_file=$(find "$work_dir/out" -maxdepth 1 -type f -name "*.zip" | head -n 1)
if [[ -z "$source_file" ]]; then
    echo "[ERROR] - No packaged ROM archive found in out/"
    exit 1
fi

mv -f "$source_file" "$output_file"
echo "$final_name" > "$work_dir/bin/ddevice/output_zip.txt"

remote_name="${RCLONE_REMOTE_NAME:-gdrive}"
remote_dir="${RCLONE_UPLOAD_DIR:-}"
if [[ -z "$remote_dir" ]]; then
    echo "[ERROR] - Missing RCLONE_UPLOAD_DIR"
    exit 1
fi

remote_path="${remote_name}:${remote_dir}"
upload "Uploading DeadZone Lite to Google Drive"
rclone --config="$work_dir/rclone.conf" copyto "$output_file" "${remote_path}/${final_name}" > /dev/null 2>&1

file_id=$(rclone --config="$work_dir/rclone.conf" lsjson "${remote_path}" | jq -r --arg name "$final_name" '.[] | select(.Name == $name) | .ID' | head -n 1)
if [[ -z "$file_id" || "$file_id" == "null" ]]; then
    echo "[ERROR] - Uploaded file ID could not be resolved"
    exit 1
fi

drive_link="https://drive.google.com/file/d/${file_id}/view?usp=sharing"
echo "$drive_link" > "$work_dir/bin/ddevice/drive_link.txt"

upload "Cleaning workspace"
rm -rf "$work_dir/build"
