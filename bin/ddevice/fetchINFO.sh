#!/bin/bash
set -euo pipefail

work_dir=$(pwd)
source "$work_dir/functions.sh"

clean_device_name() {
    local raw="$1"
    local best=""
    local part=""
    local seen="|"

    while IFS= read -r part; do
        part=$(printf '%s' "$part" | sed 's/^[[:space:]]*//; s/[[:space:]]*$//')
        [[ -z "$part" ]] && continue
        [[ "$seen" == *"|$part|"* ]] && continue
        seen="${seen}${part}|"

        if [[ -z "$best" ]]; then
            best="$part"
            continue
        fi

        if [[ "$part" == *"5G"* && "$best" != *"5G"* ]]; then
            best="$part"
            continue
        fi

        if [[ ${#part} -gt ${#best} ]]; then
            best="$part"
        fi
    done < <(printf '%s\n' "$raw" | tr '|' '\n')

    if [[ -z "$best" ]]; then
        best="Unknown Xiaomi Device"
    fi

    printf '%s\n' "$best"
}

regionTYPE=$(cat "$work_dir/bin/ddevice/device_type.txt")
AndroidVer=$(grep "ro.system.build.version.release" "$work_dir/build/baserom/images/system/system/build.prop" | awk 'NR==1' | cut -d '=' -f 2)
sdkLevel=$(grep "ro.system.build.version.sdk" "$work_dir/build/baserom/images/system/system/build.prop" | awk 'NR==1' | cut -d '=' -f 2)
device_code=$(cat "$work_dir/bin/ddevice/device_code.txt")
name=$(clean_device_name "$(cat "$work_dir/bin/ddevice/name_devices.txt")")
base_rom_code=$(cat "$work_dir/bin/ddevice/base_rom_code.txt")
rom_os=$(cat "$work_dir/bin/ddevice/rom_os.txt")
lite_version=$(cat "$work_dir/Version")
systemtype=$(cat "$work_dir/bin/ddevice/fstype.txt")
platform=$(printf '%s' "$base_rom_code" | sed -n 's/^\(OS[0-9]\+\.[0-9]\+\).*/\1/p')
if [[ -z "$platform" ]]; then
    platform="Unknown"
fi

if grep -q "ro.build.ab_update=true" build/baserom/images/vendor/build.prop; then
    echo "VAB" > "$work_dir/bin/script2flash/META-INF/Data/Structure"
else
    echo "Non-VAB" > "$work_dir/bin/script2flash/META-INF/Data/Structure"
fi

if [[ -f "$work_dir/build/baserom/images/vendor/etc/init/hw/init.qcom.rc" ]]; then
    echo "Snapdragon" > "$work_dir/bin/script2flash/META-INF/Data/Chip"
else
    echo "Mediatek" > "$work_dir/bin/script2flash/META-INF/Data/Chip"
fi

echo "$rom_os" > "$work_dir/bin/ddevice/os_type.txt"
echo "$AndroidVer" > "$work_dir/bin/ddevice/androidver.txt"
echo "$AndroidVer" > "$work_dir/bin/ddevice/android_version.txt"
echo "$sdkLevel" > "$work_dir/bin/ddevice/sdkLevel.txt"
echo "$name" > "$work_dir/bin/ddevice/device_name.txt"
echo "$base_rom_code" > "$work_dir/bin/ddevice/rom_version.txt"
echo "$regionTYPE" > "$work_dir/bin/ddevice/region.txt"
echo "$platform" > "$work_dir/bin/ddevice/platform.txt"

echo "$AndroidVer" > "$work_dir/bin/script2flash/META-INF/Data/AndroidVer"
echo "$base_rom_code" > "$work_dir/bin/script2flash/META-INF/Data/RomBased"
echo "$lite_version" > "$work_dir/bin/script2flash/META-INF/Data/Version"
echo "$regionTYPE" > "$work_dir/bin/script2flash/META-INF/Data/Region"
echo "$name" > "$work_dir/bin/script2flash/META-INF/Data/DeviceName"
echo "$systemtype" > "$work_dir/bin/script2flash/META-INF/Data/Types"

echo "------------------ DeadZone Lite Build Info ------------------"
echo "- Device Name: $name"
echo "- Codename: $device_code"
echo "- ROM Family: $rom_os"
echo "- Region: $regionTYPE"
echo "- Android: $AndroidVer"
echo "- ROM Version: $base_rom_code"
echo "- Lite Version: $lite_version"
echo "- Filesystem: $systemtype"
echo "-------------------------------------------------------------"
