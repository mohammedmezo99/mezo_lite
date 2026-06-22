work_dir=$(pwd)
source $work_dir/functions.sh
MAIN_FOLDER="$work_dir/build/baserom/images"
repS="python3 $work_dir/bin/strRep.py"
deviceTYPE=$(cat $work_dir/bin/ddevice/device_type.txt)
APKEDITOR="java -jar $work_dir/bin/apktool/apke.jar"
repS="python3 $work_dir/bin/strRep.py"


MOD_NAME="Notification Fix PowerKeeper"
patch "Patching PowerKeeper"
mkdir -p $work_dir/apk_temp
isPowerKeeper=$(find_apk_or_skip "$MOD_NAME" "PowerKeeper.apk") || exit 0
isPowerKeeperDIR=$(dirname "$isPowerKeeper")
FOLDER="$work_dir/apk_temp/isPowerKeeper.apk.out"
$APKEDITOR d -t raw -f -no-dex-debug -i "$isPowerKeeper" -o "$FOLDER" >/dev/null 2>&1 || true
apk_out_exists_or_skip "$MOD_NAME" "$FOLDER" || { rm -rf "$work_dir/apk_temp"; exit 0; }
Smali1=$(safe_find_smali "$MOD_NAME" "$FOLDER" "GmsObserver.smali") || { rm -rf "$work_dir/apk_temp"; exit 0; }
Smali2=$(safe_find_smali "$MOD_NAME" "$FOLDER" "MilletConfig.smali") || { rm -rf "$work_dir/apk_temp"; exit 0; }
tar1="$work_dir/bin/package/NOTIFICATION_FIX/A14/patch/gms.ini"
tar2="$work_dir/bin/package/NOTIFICATION_FIX/A14/patch/handle.ini"

find "$FOLDER" -type f -name "*.smali" -exec sed -i 's/Lmiui\/os\/Build;->IS_INTERNATIONAL_BUILD:Z/Lmiui\/os\/Build;->IS_MIUI:Z/g' {} +

find "$FOLDER" -type f -exec sed -i 's/"_global"/""/g' {} +

$repS $tar1 $Smali1
$repS $tar2 $Smali2

#Finishing
PowerKeeper=$(basename "$isPowerKeeper")
$APKEDITOR b -f -i "$FOLDER" -o "$work_dir/apk_temp/final/$PowerKeeper" >/dev/null 2>&1

if [ -f "$work_dir/apk_temp/final/$PowerKeeper" ]; then
    rm -rf "$isPowerKeeperDIR"/*
    cp -rf "$work_dir/apk_temp/final/$PowerKeeper" "$isPowerKeeperDIR"
fi

rm -rf "$work_dir/apk_temp"
patch "Done"
