#!/bin/bash
set -euo pipefail

baserom="$1"
work_dir=$(pwd)
tools_dir="${work_dir}/bin/$(uname)/$(uname -m)"
export PATH="${tools_dir}:$PATH"

chmod 777 "${work_dir}/bin/"*
chmod 777 "${work_dir}/bin/Linux/x86_64/"*
source "$work_dir/functions.sh"

if [[ $(git branch --show-current) == "beta" ]]; then
    polyxver="$(cat Version)"
    status="Development"
else
    polyxver="$(cat Version)"
    status="Official"
fi

check unzip aria2c 7z zip java zipalign python3 zstd bc
check jq brotli simg2img lpmake make_ext4fs mkfs.erofs payload-extract

rm -rf "$work_dir/out"
rm -rf "$work_dir/build"

source "$work_dir/bin/ddevice/getROM.sh" "$baserom"

if unzip -l "${baserom}" | grep -q "payload.bin"; then
    baserom_type="payload"
    echo "$baserom_type" > "$work_dir/bin/ddevice/romtype.txt"
    unpack "Found payload.bin file"
    super_list="vendor mi_ext odm odm_dlkm system system_dlkm vendor_dlkm product product_dlkm system_ext"
    unpack "ROM validation passed."
elif unzip -l "${baserom}" | grep -q "br$"; then
    baserom_type="br"
    echo "$baserom_type" > "$work_dir/bin/ddevice/romtype.txt"
    super_list="system vendor product odm system_ext mi_ext"
    unpack "Found Brotli partitions"
    unpack "ROM validation passed."
elif unzip -l "${baserom}" | grep -q "images/super.img*"; then
    unpack "Found split super.img files"
    is_base_rom_eu=true
    unpack "ROM validation passed."
else
    error "Unpack failed"
    exit 1
fi

rm -rf app
rm -rf tmp
rm -rf config
rm -rf build/baserom/
find . -type d -name 'miui_*' | xargs rm -rf

unpack "Files cleaned up."
mkdir -p build/baserom/images/

require_matching_files() {
    local base_dir="$1"
    local pattern="$2"
    local message="$3"

    if ! find "$base_dir" -maxdepth 1 -type f -name "$pattern" | grep -q .; then
        error "$message"
        exit 1
    fi
}

if [[ ${baserom_type:-} == "payload" ]]; then
    unpack "Extracting payload.bin"
    unzip "${baserom}" payload.bin -d build/baserom >/dev/null 2>&1 || error "Extracting payload.bin failed"
    unpack "payload.bin extracted."
elif [[ ${baserom_type:-} == "br" ]]; then
    unpack "Extracting *.new.dat.br"
    unzip "${baserom}" -d build/baserom >/dev/null 2>&1 || error "Extracting new.dat.br failed"
    unpack "Partition archives extracted."
elif [[ ${is_base_rom_eu:-false} == true ]]; then
    unpack "Extracting super.img files"
    unzip "${baserom}" 'images/*' -d build/baserom >/dev/null 2>&1 || error "Extracting super.img failed"
    unpack "Merging split super.img files"
    simg2img build/baserom/images/super.img.* build/baserom/images/super.img
    rm -rf build/baserom/images/super.img.*
    mv build/baserom/images/super.img build/baserom/super.img
    if [[ -f build/baserom/images/cust.img.0 ]]; then
        simg2img build/baserom/images/cust.img.* build/baserom/images/cust.img
        rm -rf build/baserom/images/cust.img.*
    fi
fi

if [[ ${baserom_type:-} == "payload" ]]; then
    unpack "Unpacking payload.bin"
    payload-extract extract -o build/baserom/images/ build/baserom/payload.bin >/dev/null 2>&1 || error "Unpacking payload.bin failed"
    require_matching_files "$work_dir/build/baserom/images" "*.img" "Payload extraction produced no .img files"
elif [[ ${baserom_type:-} == "br" ]]; then
    super_list=$(grep "add " build/baserom/dynamic_partitions_op_list | awk '{ print $2 }')
    unpack "Converting Brotli partitions"
    for brotlipart in ${super_list}; do
        brotli -d "build/baserom/${brotlipart}.new.dat.br" >/dev/null 2>&1
        python3 "$work_dir/bin/Linux/x86_64/sdat2img.py" "build/baserom/${brotlipart}.transfer.list" "build/baserom/${brotlipart}.new.dat" "build/baserom/images/${brotlipart}.img" >/dev/null 2>&1
        rm -rf "build/baserom/${brotlipart}.new.dat" "build/baserom/${brotlipart}.new.dat.br" "build/baserom/${brotlipart}.transfer.list" "build/baserom/${brotlipart}.patch.dat"
    done
    require_matching_files "$work_dir/build/baserom/images" "*.img" "Brotli extraction produced no .img files"
elif [[ ${is_base_rom_eu:-false} == true ]]; then
    unpack "Unpacking super.img"
    super_list=$(python3 bin/lpunpack.py --info build/baserom/super.img | grep "super:" | awk '{ print $5 }')
    for i in ${super_list}; do
        if [[ $i == *_a ]]; then
            i=${i%_a}
            python3 bin/lpunpack.py -p "${i}_a" build/baserom/super.img build/baserom/images >/dev/null 2>&1
            mv "build/baserom/images/${i}_a.img" "build/baserom/images/${i}.img"
        else
            python3 bin/lpunpack.py -p "${i}" build/baserom/super.img build/baserom/images >/dev/null 2>&1
        fi
    done
    super_list=$(echo "$super_list" | sed 's/_a//g')
    require_matching_files "$work_dir/build/baserom/images" "*.img" "super.img extraction produced no .img files"
fi

if [[ ! -d "$work_dir/build/baserom/images" ]]; then
    error "Missing build/baserom/images after extraction"
    exit 1
fi

for part in ${super_list}; do
    if [[ ! -f "$work_dir/build/baserom/images/${part}.img" ]]; then
        error "Missing required partition image: ${part}.img"
        exit 1
    fi
    extract_partition "$work_dir/build/baserom/images/${part}.img" "$work_dir/build/baserom/images"
    PACK_TYPE=$(cat "$work_dir/bin/ddevice/fstype.txt")
done

if [[ ! -d "$work_dir/build/baserom/images/system" && ! -d "$work_dir/build/baserom/images/system/system" ]]; then
    error "System partition extraction is incomplete"
    exit 1
fi

if [[ ! -d "$work_dir/build/baserom/images/vendor" ]]; then
    error "Vendor partition extraction is incomplete"
    exit 1
fi

echo "$device_f" > "$work_dir/bin/ddevice/device_f.txt"
getvar=$(cat "$work_dir/bin/ddevice/device_f.txt")

rm -rf config

if [[ -f "$work_dir/${baserom}.zip" ]]; then
    rm -rf "${baserom}.zip"
fi

rm -rf build/baserom/payload.bin
rm -rf build/baserom/images/super.img

mods "Gathering device information"
bash "$work_dir/bin/ddevice/getname.sh" "$getvar"
bash "$work_dir/bin/ddevice/fetchINFO.sh"
python3 "$work_dir/notify.py" private build_started

bash "$work_dir/bin/ddevice/DEBLOAT/debloat.sh"
info "Done"

bash "$work_dir/bin/modfile/OS1/insmod.sh"
bash "$work_dir/bin/modfile/OS2/insmod.sh"
bash "$work_dir/bin/modfile/OS3/insmod.sh"
bash "$work_dir/bin/modfile/Universal/insfile.sh"
bash "$work_dir/bin/modfile/UpdateFile/insupdate.sh"
bash "$work_dir/bin/package/patchpackage.sh"

find "$work_dir/build/baserom/images/" -exec touch -t 200901010000.00 {} + 2>/dev/null || true
