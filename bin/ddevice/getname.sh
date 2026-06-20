#!/bin/bash
set -euo pipefail

work_dir=$(pwd)
source "$work_dir/functions.sh"

file_json="$work_dir/bin/ddevice/data/devices.json"
key="${1:-$(cat "$work_dir/bin/ddevice/device_f.txt")}"

exact_key=$(grep -ix "$key" "$work_dir/bin/ddevice/data/devices_data.txt" 2>/dev/null || grep -ix "$key" "$work_dir/bin/ddevice/data/pad_data.txt" 2>/dev/null || true)
if [[ -z "$exact_key" ]]; then
    exact_key="$key"
fi

value=$(jq -r --arg key "$exact_key" '.[$key] // "Unknown device"' "$file_json")
echo "$value" > "$work_dir/bin/ddevice/name_devices.txt"
