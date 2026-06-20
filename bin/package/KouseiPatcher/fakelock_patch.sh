#!/bin/bash
# SPDX-License-Identifier: GPL-3.0

work_dir=$(pwd)
magiskboot="$work_dir/bin/magiskboot"
prop="$work_dir/bin/package/KouseiPatcher/prop"
SEARCH_DIR="build/baserom/images"
BUILD_PROP=$(find "$SEARCH_DIR" -type f -name "build.prop" | head -n 1)
first_api=$(grep "ro.product.first_api_level" "$BUILD_PROP" | awk 'NR==1' | cut -d '=' -f 2 | tr -d ' \r')
androidVER=$(cat $work_dir/bin/ddevice/androidver.txt | tr -d ' \r\n' | cut -d '.' -f 1)
echo "[DEBUG] androidVER raw hex: $(cat $work_dir/bin/ddevice/androidver.txt | xxd | head -n 2)"
echo "[DEBUG] androidVER after clean: '$androidVER'"
echo "[DEBUG] androidVER length: $(echo -n "$androidVER" | wc -c)"

if [ "$androidVER" -lt 14 ]; then
    mods "Android lower than 14!Inject XEUToolbox by Xiaomi.eu"
    echo "/system_ext/xbin/xeu_toolbox  u:object_r:toolbox_exec:s0" >> build/baserom/images/config/system_ext_file_contexts
    echo "/system_ext/xbin/xeu_toolbox  u:object_r:toolbox_exec:s0" >> build/baserom/images/system_ext/etc/selinux/system_ext_file_contexts
    echo "(allow init toolbox_exec (file ((execute_no_trans))))" >> build/baserom/images/system_ext/etc/selinux/system_ext_sepolicy.cil
    cp -rf $work_dir/bin/package/KouseiPatcher/bin/xeutoolbox/* $work_dir/build/baserom/images/system_ext
    mods "Done!"
else
  if [ -f $work_dir/build/baserom/images/vendor_boot.img ]; then 

  echo "[IMGPATCH] - PATCHING vendor_boot.img"
  mkdir -p $work_dir/temp_boot

  echo "[IMGPATCH] - Stage 1 Patching..."
  cp -rf $work_dir/build/baserom/images/vendor_boot.img $work_dir
  cp -rf $work_dir/build/baserom/images/vendor_boot.img $work_dir/temp_boot
  $magiskboot unpack -h $work_dir/vendor_boot.img >/dev/null 2>&1
  sed -i '/^cmdline=/ s/$/ androidboot.verifiedbootstate=green androidboot.vbmeta.device_state=locked/' $work_dir/header

  echo "[IMGPATCH] - Stage 2 Patching..."
  $magiskboot repack $work_dir/vendor_boot.img >/dev/null 2>&1
  mv $work_dir/new-boot.img $work_dir/vendor_boot.img

  echo "[IMGPATCH] - Stage 3 Cleanup..."
  rm -rf $work_dir/dtb
  rm -rf $work_dir/header
  rm -rf $work_dir/ramdisk.cpio
  rm -rf $work_dir/build/baserom/images/vendor_boot.img
  mv $work_dir/vendor_boot.img $work_dir/build/baserom/images

  if [ -f $work_dir/build/baserom/images/vendor_boot.img ]; then
    echo "[IMGPATCH] - Patched vendor_boot.img sucessfully!"
    rm -rf $work_dir/temp_boot
  else
    echo "[IMGPATCH] - Failed to patch vendor_boot.img!Revert vendor_boot.img"
    mv $work_dir/temp_boot/vendor_boot.img $work_dir/build/baserom/images
    rm -rf $work_dir/temp_boot
  fi

  fi
fi

cat $prop/build.prop >> $work_dir/build/baserom/images/system/system/build.prop
if [[ $androidVER == "12" ]]; then
cat $prop/cust.prop >> $work_dir/build/baserom/images/system/system/etc/cust/cust_prop_white_keys_list
else
cat $prop/cust.prop >> $work_dir/build/baserom/images/system_ext/etc/cust_prop_white_keys_list
patch "Done"
fi