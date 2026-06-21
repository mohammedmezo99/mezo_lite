#!/bin/bash

baserom="$1"
work_dir=$(pwd)
source $work_dir/functions.sh

clean_codename() {
    local raw="$1"
    local lower
    lower=$(printf '%s' "$raw" | tr '[:upper:]' '[:lower:]')
    lower=${lower%%|*}
    lower=${lower%%-*}
    lower=${lower%%_*}

    for suffix in globalstable chinastable indiastable indonesiastable eeastable europestable russiastable turkeystable taiwanstable japanstable global china india indonesia eea europe russia turkey taiwan japan stable; do
        if [[ "$lower" == *"$suffix" ]]; then
            lower="${lower%$suffix}"
        fi
    done

    lower=$(printf '%s' "$lower" | sed 's/[^a-z0-9]//g')
    printf '%s\n' "$lower"
}

# Check whether it is a local package or a link
if [ ! -f "${baserom}" ] && [ "$(echo $baserom |grep http)" != "" ]; then
    info "Download link detected, starting a download..."
    aria2c --max-download-limit=1024M --file-allocation=none -s10 -x10 -j10 ${baserom}
    baserom=$(basename ${baserom} | sed 's/\?t.*//')
    if [ -f $work_dir/topaz-ota_full-OS3.0.2.0.WMGCNXM-user-16.0-b487e82659.zip ]; then
        baserom="topaz-ota_full-OS3.0.2.0.WMGCNXM-user-16.0-b487e82659.zip"
        info "BASEROM: ${baserom}"
    elif [ -f $work_dir/munch-ota_full-OS2.0.215.0.VLMCNXM-user-15.0-7df6d5ee94.zip ]; then
        baserom="munch-ota_full-OS2.0.215.0.VLMCNXM-user-15.0-7df6d5ee94.zip"
        info "BASEROM: ${baserom}"
    elif [ ! -f "${baserom}" ]; then
        error "Download error!"
    fi
elif [ -f "${baserom}" ]; then
    info "BASEROM: ${baserom}"
else
    error "BASEROM: Invalid parameter"
    exit
fi

rom_filename=$(basename "$baserom")
rom_codename=$(printf '%s' "$rom_filename" | sed -n 's/^\([^-][^-]*\)-ota_full-.*/\1/p')

# Get ROM Info
if [ "$(echo $baserom |grep miui_)" != "" ]; then
    device_code=$(basename $baserom |cut -d '_' -f 2)
    base_rom_code=$(echo "$baserom" | awk -F'_' '{print $3}')
elif [ "$(echo $baserom |grep xiaomi.eu_)" != "" ]; then
    device_code=$(basename $baserom |cut -d '_' -f 3)
    base_rom_code=$(echo "$baserom" | awk -F'_' '{print $3}')
elif [ "$(echo $baserom | grep -E '.*-ota_full-.*')" != "" ]; then
    device_code=$(basename $baserom | cut -d '-' -f 1)
    base_rom_code=$(basename $baserom | cut -d '-' -f 3)

    # Transform device_code
    device_code=$(echo $device_code | awk -F '_' '{
        if (NF == 1) {
            # If one part, e.g., shennong
            print toupper($1)
        } else if (NF == 2) {
            # If two parts, e.g., tapas_global
            print toupper($1) toupper(substr($2, 1, 1)) substr($2, 2)
        } else if (NF == 3) {
            # If three parts, e.g., houji_tw_global
            printf toupper($1) toupper($2) toupper(substr($3, 1, 1)) substr($3, 2)
        }
    }')
else
    device_code="YourDevice"
    base_rom_code="Unknown"
fi

if [[ -n "$rom_codename" ]]; then
    cleaned_rom_codename=$(clean_codename "$rom_codename")
    if [[ -n "$cleaned_rom_codename" ]]; then
        device_f="$cleaned_rom_codename"
        device_code=$(printf '%s' "$cleaned_rom_codename" | tr '[:lower:]' '[:upper:]')
    fi
fi

device_f=$(echo $device_code | sed 's/\(Global\|EEAGlobal\|INGlobal\|IDGlobal\|RUGlobal\|TWGlobal\|TRGlobal\|JPGlobal\)$//' | tr '[:upper:]' '[:lower:]')
device_f=$(clean_codename "$device_f")
if [[ -n "$device_f" ]]; then
    device_code=$(printf '%s' "$device_f" | tr '[:lower:]' '[:upper:]')
fi

# Determine Device Type
info "Get Device Type"
if echo "$device_code" | grep -q 'EEAGlobal'; then
    DEVICE_TYPE="EEAGlobal"
elif echo "$device_code" | grep -q 'INGlobal'; then
    DEVICE_TYPE="INGlobal"
elif echo "$device_code" | grep -q 'IDGlobal'; then
    DEVICE_TYPE="IDGlobal"
elif echo "$device_code" | grep -q 'RUGlobal'; then
    DEVICE_TYPE="RUGlobal"
elif echo "$device_code" | grep -q 'JPGlobal'; then
    DEVICE_TYPE="JPGlobal"
elif echo "$device_code" | grep -q 'Global'; then
    DEVICE_TYPE="Global"
elif echo "$device_code" | grep -q 'TWGlobal'; then
    DEVICE_TYPE="TWGlobal"
elif echo "$device_code" | grep -q 'TRGlobal'; then
    DEVICE_TYPE="TRGlobal"
else
    DEVICE_TYPE="China"
fi

#Check MIUI or Hyper
if echo "$base_rom_code" | grep -q "OS1"; then
    ROM_OS="OS1"
elif echo "$base_rom_code" | grep -q "OS2"; then
    ROM_OS="OS2"
elif echo "$base_rom_code" | grep -q "OS3"; then
    ROM_OS="OS3"
elif echo "$base_rom_code" | grep -q "V14"; then
    ROM_OS="MIUI"
elif echo "$base_rom_code" | grep -q "V13"; then
    ROM_OS="MIUI"
else
    echo "Unsupport ROM Exiting..."
    exit 1
fi

echo $base_rom_code > $work_dir/bin/ddevice/base_rom_code.txt
echo $base_rom_code > $work_dir/bin/ddevice/rom_version.txt
echo $base_rom_code > $work_dir/bin/ddevice/os_code.txt
echo $device_code > $work_dir/bin/ddevice/device_code.txt
echo $device_f > $work_dir/bin/ddevice/codename.txt
echo $DEVICE_TYPE > $work_dir/bin/ddevice/device_type.txt
echo $DEVICE_TYPE > $work_dir/bin/ddevice/region.txt
echo $ROM_OS > $work_dir/bin/ddevice/rom_os.txt
