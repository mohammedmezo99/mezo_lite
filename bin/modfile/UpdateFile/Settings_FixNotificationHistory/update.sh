WORK_DIR=$(pwd)
source $WORK_DIR/functions.sh
MAIN_FOLDER="$WORK_DIR/build/baserom/images"
rom_os=$(cat $WORK_DIR/bin/ddevice/rom_os.txt)
regionTYPE=$(cat $WORK_DIR/bin/ddevice/device_type.txt)
AndroidVER=$(cat $WORK_DIR/bin/ddevice/androidver.txt)
APKEDITOR="java -jar $WORK_DIR/bin/apktool/apke.jar"
repS="python3 $WORK_DIR/bin/strRep.py"

#Add Settings Lab To Settings
MOD_NAME="Settings Fix Notification History"
mods "Fixing Notification History"
mkdir -p $WORK_DIR/apk_temp
isSettings=$(find_apk_or_skip "$MOD_NAME" "Settings.apk") || exit 0
isSettingsDIR=$(dirname "$isSettings")
OUT_DIR="$WORK_DIR/apk_temp/isSettings.apk.out"
$APKEDITOR d -i "$isSettings" -o "$OUT_DIR" >/dev/null 2>&1 || true
apk_out_exists_or_skip "$MOD_NAME" "$OUT_DIR" || { rm -rf "$WORK_DIR/apk_temp"; exit 0; }
p1=$(safe_find_smali "$MOD_NAME" "$OUT_DIR" "notification_history.xml") || { rm -rf "$WORK_DIR/apk_temp"; exit 0; }
res="$OUT_DIR/resources/package_1/res"

#patching
mods "Starting..."
sed -i -e 's/?android:attr\/colorBackgroundFloating/@drawable\/card_view_corner/g' -e 's/rounded_bg/device_card_back_ground/g' "$p1"
mods "Stage 1 Done"

#Finishing
mods "Rebuild..."
Settings=$(basename "$isSettings")
$APKEDITOR b -f -i "$OUT_DIR" -o "$WORK_DIR/apk_temp/final/$Settings" >/dev/null 2>&1

if [ -f "$WORK_DIR/apk_temp/final/$Settings" ]; then
  mods "Cleaning WorkSpace"
  rm -rf "$isSettingsDIR"/*
  mods "Finish Modding"
  cp -rf "$WORK_DIR/apk_temp/final/$Settings" "$isSettingsDIR"
  mods "Cleaned!"
  
fi

rm -rf "$WORK_DIR/apk_temp"
mods "Done"
