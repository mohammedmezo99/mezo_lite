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

transform_region_display_code() {
    local raw="$1"
    echo "$raw" | awk -F '_' '{
        if (NF == 1) {
            print toupper($1)
        } else if (NF == 2) {
            print toupper($1) toupper(substr($2, 1, 1)) substr($2, 2)
        } else if (NF >= 3) {
            printf toupper($1)
            for (i = 2; i <= NF; i++) {
                printf toupper(substr($i, 1, 1)) substr($i, 2)
            }
            printf "\n"
        }
    }'
}

detect_device_type() {
    local code_lower
    code_lower=$(printf '%s' "$1" | tr '[:upper:]' '[:lower:]')

    case "$code_lower" in
        *eea_global*|*eeaglobal*|*eea*) echo "EEAGlobal" ;;
        *in_global*|*inglobal*|*india*) echo "INGlobal" ;;
        *id_global*|*idglobal*|*indonesia*) echo "IDGlobal" ;;
        *ru_global*|*ruglobal*|*russia*) echo "RUGlobal" ;;
        *tw_global*|*twglobal*|*taiwan*) echo "TWGlobal" ;;
        *tr_global*|*trglobal*|*turkey*) echo "TRGlobal" ;;
        *jp_global*|*jpglobal*|*japan*) echo "JPGlobal" ;;
        *global*) echo "Global" ;;
        *) echo "China" ;;
    esac
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
region_source=""

# Get ROM Info
if [ "$(echo $baserom |grep miui_)" != "" ]; then
    device_code=$(basename $baserom |cut -d '_' -f 2)
    base_rom_code=$(echo "$baserom" | awk -F'_' '{print $3}')
    region_source="$device_code"
elif [ "$(echo $baserom |grep xiaomi.eu_)" != "" ]; then
    device_code=$(basename $baserom |cut -d '_' -f 3)
    base_rom_code=$(echo "$baserom" | awk -F'_' '{print $3}')
    region_source="$device_code"
elif [ "$(echo $baserom | grep -E '.*-ota_full-.*')" != "" ]; then
    device_code=$(basename $baserom | cut -d '-' -f 1)
    base_rom_code=$(basename $baserom | cut -d '-' -f 3)
    region_source="$device_code"
    device_code=$(transform_region_display_code "$device_code")
else
    device_code="YourDevice"
    base_rom_code="Unknown"
    region_source="$device_code"
fi

if [[ -z "$region_source" && -n "$rom_codename" ]]; then
    region_source="$rom_codename"
fi

raw_region_code="$device_code"
if [[ -n "$rom_codename" ]]; then
    transformed_rom_code=$(transform_region_display_code "$rom_codename")
    if [[ -n "$transformed_rom_code" ]]; then
        raw_region_code="$transformed_rom_code"
    fi
fi

# Determine Device Type
info "Get Device Type"
DEVICE_TYPE=$(detect_device_type "$raw_region_code")

device_f=$(clean_codename "${rom_codename:-$region_source}")
if [[ -z "$device_f" ]]; then
    device_f=$(clean_codename "$region_source")
fi

if [[ -z "$device_f" ]]; then
    error "Unable to determine clean device codename from $baserom"
    exit 1
fi

device_code="$raw_region_code"

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
echo $device_f > $work_dir/bin/ddevice/device_f.txt
echo $device_f > $work_dir/bin/ddevice/codename.txt
echo $DEVICE_TYPE > $work_dir/bin/ddevice/device_type.txt
echo $DEVICE_TYPE > $work_dir/bin/ddevice/region.txt
echo $ROM_OS > $work_dir/bin/ddevice/rom_os.txt
