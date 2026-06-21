#!/bin/bash
set -euo pipefail

work_dir=$(pwd)
source "$work_dir/functions.sh"

tools_dir="${work_dir}/bin/$(uname)/$(uname -m)"
export PATH="${tools_dir}:$PATH"

super_list="vendor mi_ext odm odm_dlkm system system_dlkm vendor_dlkm product product_dlkm system_ext"
androidVER=$(< "$work_dir/bin/ddevice/androidver.txt")
getvar=$(< "$work_dir/bin/ddevice/device_f.txt")
PACK_TYPE=$(< "$work_dir/bin/ddevice/fstype.txt")

superSize=$(bash "$work_dir/bin/getSuperSize.sh" "$getvar")
repack "$superSize"
repack "Super image size: ${superSize}"
repack "Packing super.img"

for pname in ${super_list}; do
    if [[ -d "$work_dir/build/baserom/images/$pname" ]]; then
        thisSize=$(du -sb "$work_dir/build/baserom/images/${pname}" | awk '{print $1}')
        if [[ $androidVER == "12" ]]; then
            case $pname in
                odm) addSize=104217728 ;;
                system) addSize=114217728 ;;
                vendor) addSize=104217728 ;;
                system_ext) addSize=104217728 ;;
                product) addSize=104217728 ;;
                *) addSize=8054432 ;;
            esac
        else
            case $pname in
                mi_ext|odm|system|vendor|system_ext|product) addSize=100000000 ;;
                *) addSize=8054432 ;;
            esac
        fi

        thisSize=$(echo "$thisSize + $addSize" | bc)
        if [[ "$PACK_TYPE" == "EXT" ]]; then
            python3 "$work_dir/bin/fix_selinux.py" "$work_dir/build/baserom/images/${pname}" "$work_dir/build/baserom/images/config/${pname}_fs_config" "$work_dir/build/baserom/images/config/${pname}_file_contexts" >/dev/null 2>&1
            make_ext4fs -J -T "$(date +%s)" -S "$work_dir/build/baserom/images/config/${pname}_file_contexts" -l "$thisSize" -C "$work_dir/build/baserom/images/config/${pname}_fs_config" -L "${pname}" -a "${pname}" "$work_dir/build/baserom/images/${pname}.img" "$work_dir/build/baserom/images/${pname}" >/dev/null 2>&1
        elif [[ "$PACK_TYPE" == "EROFS" ]]; then
            python3 "$work_dir/bin/fix_selinux.py" "$work_dir/build/baserom/images/${pname}" "$work_dir/build/baserom/images/config/${pname}_fs_config" "$work_dir/build/baserom/images/config/${pname}_file_contexts" >/dev/null 2>&1
            mkfs.erofs --quiet -zlz4hc,9 --mount-point "${pname}" --fs-config-file="$work_dir/build/baserom/images/config/${pname}_fs_config" --file-contexts="$work_dir/build/baserom/images/config/${pname}_file_contexts" "$work_dir/build/baserom/images/${pname}.img" "$work_dir/build/baserom/images/${pname}" >/dev/null 2>&1
        else
            error "Unable to handle image format"
            exit 1
        fi

        if [[ -f "$work_dir/build/baserom/images/${pname}.img" ]]; then
            repack "Packed ${pname}.img"
        else
            repack "Packing ${pname}.img failed"
        fi
    fi
done

if grep -q "ro.build.ab_update=true" build/baserom/images/vendor/build.prop; then
    is_ab_device=true
else
    is_ab_device=false
fi

if [[ "$is_ab_device" == false ]]; then
    repack "Packing super.img for A-only device"
    GROUP_SIZE=$((superSize - 268435456))
    lpargs="-F --output build/baserom/images/super.img --metadata-size 65536 --super-name super --metadata-slots 2 --block-size 4096 --device super:$superSize --group=qti_dynamic_partitions:$GROUP_SIZE"

    for pname in odm mi_ext system system_ext product vendor; do
        if [[ -f "build/baserom/images/${pname}.img" ]]; then
            if [[ "$OSTYPE" == "darwin"* ]]; then
                subsize=$(stat -f%z "build/baserom/images/${pname}.img")
            else
                subsize=$(du -sb "build/baserom/images/${pname}.img" | awk '{print $1}')
            fi
            repack "Super sub-partition ${pname} size: ${subsize}"
            lpargs="$lpargs --partition ${pname}:readonly:${subsize}:qti_dynamic_partitions --image ${pname}=build/baserom/images/${pname}.img"
        fi
    done
else
    repack "Packing super.img for V-AB device"
    GROUP_SIZE=$((superSize - 268435456))
    lpargs="-F --virtual-ab --output $work_dir/build/baserom/images/super.img --metadata-size 65536 --super-name super --metadata-slots 3 --block-size 4096 --device super:$superSize --group=qti_dynamic_partitions_a:$GROUP_SIZE --group=qti_dynamic_partitions_b:$GROUP_SIZE"

    for pname in ${super_list}; do
        if [[ -f "build/baserom/images/${pname}.img" ]]; then
            subsize=$(du -sb "build/baserom/images/${pname}.img" | awk '{print $1}')
            repack "Super sub-partition ${pname} size: ${subsize}"
            lpargs="$lpargs --partition ${pname}_a:readonly:${subsize}:qti_dynamic_partitions_a --image ${pname}_a=build/baserom/images/${pname}.img --partition ${pname}_b:readonly:0:qti_dynamic_partitions_b"
        fi
    done
fi

lpmake $lpargs

if [[ -f "$work_dir/build/baserom/images/super.img" ]]; then
    repack "Successfully packed super.img."
else
    repack "Unable to pack super.img."
    exit 1
fi

package_root="$work_dir/out/package"
package_images_dir="$package_root/images"
rm -rf "$package_root"
mkdir -p "$package_images_dir"

repack "Preparing flash package"
cp -rf "$work_dir/bin/script2flash/META-INF" "$package_root/"
cp -rf "$work_dir/bin/script2flash/"*.bat "$package_root/" 2>/dev/null || true
cp -rf "$work_dir/bin/script2flash/"*.sh "$package_root/" 2>/dev/null || true

if [[ -f "$work_dir/bin/script2flash/cust.img" ]]; then
    cp -f "$work_dir/bin/script2flash/cust.img" "$package_images_dir/"
fi

cp -f "$work_dir/build/baserom/images/super.img" "$package_root/"

mkdir -p "$work_dir/out"
rm -f "$work_dir/out/package.zip"
(
    cd "$package_root"
    zip -qr "$work_dir/out/package.zip" ./*
)
repack "Created package archive: out/package.zip"

for pname in ${super_list}; do
    rm -rf "$work_dir/build/baserom/images/${pname}.img" 2>/dev/null
done

find "$work_dir/build" -exec touch -t 200901010000.00 {} + 2>/dev/null || true
