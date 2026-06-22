WORK_DIR=$(pwd)
source $WORK_DIR/functions.sh
MAIN_FOLDER="$WORK_DIR/build/baserom/images"
androidVER=$(cat $WORK_DIR/bin/ddevice/androidver.txt)
APKEDITOR="java -jar $WORK_DIR/bin/apktool/apke.jar"
regionTYPE=$(cat $WORK_DIR/bin/ddevice/device_type.txt)

if [[ $regionTYPE == *"Global"* ]];then
    MOD_NAME="Settings Global Fix Theme"
	mods "Fixing Theme Issues"
    mkdir -p $WORK_DIR/apk_temp
    isSettings=$(find_apk_or_skip "$MOD_NAME" "Settings.apk") || exit 0
    isSettingsDIR=$(dirname "$isSettings")
    OUT_DIR="$WORK_DIR/apk_temp/isSettings.apk.out"

    $APKEDITOR d -t raw -f -no-dex-debug -i "$isSettings" -o "$OUT_DIR" >/dev/null 2>&1 || true
    apk_out_exists_or_skip "$MOD_NAME" "$OUT_DIR" || { rm -rf "$WORK_DIR/apk_temp"; exit 0; }
    isMiuiSettingsSmali=$(safe_find_smali "$MOD_NAME" "$OUT_DIR" "MiuiSettings.smali") || { rm -rf "$WORK_DIR/apk_temp"; exit 0; }

    #patching
    sed -i '
    /sget v10, Lcom\/android\/settings\/R$id;->personalize_title:I/,/sget-boolean v10, Lmiui\/os\/Build;->IS_INTERNATIONAL_BUILD:Z/ {
        /sget-boolean v10, Lmiui\/os\/Build;->IS_INTERNATIONAL_BUILD:Z/c\    const/4 v10, 0
    }
    ' "$isMiuiSettingsSmali"

    sed -i '
    /sget v10, Lcom\/android\/settings\/R$id;->theme_settings:I/,/sget-boolean v10, Lmiui\/os\/Build;->IS_INTERNATIONAL_BUILD:Z/ {
        /sget-boolean v10, Lmiui\/os\/Build;->IS_INTERNATIONAL_BUILD:Z/c\    const/4 v10, 0
    }
    ' "$isMiuiSettingsSmali"

    sed -i '
    /sget v10, Lcom\/android\/settings\/R$id;->wallpaper_settings:I/,/sget-boolean v10, Lmiui\/os\/Build;->IS_INTERNATIONAL_BUILD:Z/ {
        /sget-boolean v10, Lmiui\/os\/Build;->IS_INTERNATIONAL_BUILD:Z/c\    const/4 v10, 0
    }
    ' "$isMiuiSettingsSmali"


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
    mods "This Android version is not supported"
fi
