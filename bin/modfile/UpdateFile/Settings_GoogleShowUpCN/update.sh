WORK_DIR=$(pwd)
source $WORK_DIR/functions.sh
MAIN_FOLDER="$WORK_DIR/build/baserom/images"
repS="python3 $WORK_DIR/bin/strRep.py"
deviceTYPE=$(cat $WORK_DIR/bin/ddevice/device_type.txt)
APKEDITOR="java -jar $WORK_DIR/bin/apktool/apke.jar"

if [[ $deviceTYPE == "China" ]];then
    MOD_NAME="Settings Google Show Up CN"
    mods "Adding Google Option For China ROM"
    mkdir -p $WORK_DIR/apk_temp
    isSettings=$(find_apk_or_skip "$MOD_NAME" "Settings.apk") || exit 0
    isSettingsDIR=$(dirname "$isSettings")
    OUT_DIR="$WORK_DIR/apk_temp/isSettings.apk.out"

    $APKEDITOR d -t raw -f -no-dex-debug -i "$isSettings" -o "$OUT_DIR" >/dev/null 2>&1 || true
    apk_out_exists_or_skip "$MOD_NAME" "$OUT_DIR" || { rm -rf "$WORK_DIR/apk_temp"; exit 0; }
    isMiuiSettingsSmali=$(safe_find_smali "$MOD_NAME" "$OUT_DIR" "MiuiSettings.smali") || { rm -rf "$WORK_DIR/apk_temp"; exit 0; }

    #patching
    sed -i '/sget-boolean v0, Lmiui\/os\/Build;->IS_GLOBAL_BUILD:Z/ a\\n    const/4 v0, 0x1' "$isMiuiSettingsSmali"

    #Finishing
    Settings=$(basename "$isSettings")
    $APKEDITOR b -f -i "$OUT_DIR" -o "$WORK_DIR/apk_temp/final/$Settings" >/dev/null 2>&1

    if [ -f "$WORK_DIR/apk_temp/final/$Settings" ]; then
        rm -rf "$isSettingsDIR"/*
        cp -rf "$WORK_DIR/apk_temp/final/$Settings" "$isSettingsDIR"
    fi

    rm -rf "$WORK_DIR/apk_temp"
	mods "Done"
else
    mods "Region not support to patch"
fi
