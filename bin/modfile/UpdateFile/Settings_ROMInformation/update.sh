WORK_DIR=$(pwd)
source $WORK_DIR/functions.sh
MAIN_FOLDER="$WORK_DIR/build/baserom/images"
rom_os=$(cat $WORK_DIR/bin/ddevice/rom_os.txt)
AndroidVER=$(cat $WORK_DIR/bin/ddevice/androidver.txt)
APKEDITOR="java -jar $WORK_DIR/bin/apktool/apke.jar"
base_rom_code=$(cat $WORK_DIR/bin/ddevice/base_rom_code.txt)
myversion="$(cat $WORK_DIR/Version)"
repS="python3 $WORK_DIR/bin/strRep.py"
build_date=$(TZ=UTC date +"%y%m%d")

#patching
if [[ $rom_os == "MIUI" ]]; then 

mods "Add ROM Information To MIUI"
MOD_NAME="Settings ROM Information"
mkdir -p $WORK_DIR/apk_temp
isSettings=$(find_apk_or_skip "$MOD_NAME" "Settings.apk") || exit 0
isSettingsDIR=$(dirname "$isSettings")
OUT_DIR="$WORK_DIR/apk_temp/isSettings.apk.out"
$APKEDITOR d -i "$isSettings" -o "$OUT_DIR" >/dev/null 2>&1 || true
apk_out_exists_or_skip "$MOD_NAME" "$OUT_DIR" || { rm -rf "$WORK_DIR/apk_temp"; exit 0; }
p1=$(safe_find_smali "$MOD_NAME" "$OUT_DIR" "MiuiAboutPhoneUtils.smali") || { rm -rf "$WORK_DIR/apk_temp"; exit 0; }

mods "Add ROM Information To MIUI"
  sed -i "s/MIUI /MIUINT $myversion | /g" "$p1"
  sed -i "s/MIUI Pad /MIUINT $myversion | /g" "$p1"
  sed -i "s/MIUI Fold /MIUINT $myversion | /g" "$p1"

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
  mods "Adding MIUI Information Done!"
else
mods "Add ROM Information To HyperOS"
  MOD_NAME="Settings ROM Information"
  mkdir -p $WORK_DIR/apk_temp
  isSettings=$(find_apk_or_skip "$MOD_NAME" "Settings.apk") || exit 0
  isSettingsDIR=$(dirname "$isSettings")
  OUT_DIR="$WORK_DIR/apk_temp/isSettings.apk.out"
  $APKEDITOR d -i "$isSettings" -o "$OUT_DIR" >/dev/null 2>&1 || true
  apk_out_exists_or_skip "$MOD_NAME" "$OUT_DIR" || { rm -rf "$WORK_DIR/apk_temp"; exit 0; }
  p1=$(safe_find_smali "$MOD_NAME" "$OUT_DIR" "MiuiAboutPhoneUtils.smali") || { rm -rf "$WORK_DIR/apk_temp"; exit 0; }
  tar1="$WORK_DIR/bin/modfile/UpdateFile/Settings_ROMInformation/getMiuiVersionInCard.ini"
  tar2="$WORK_DIR/bin/modfile/UpdateFile/Settings_ROMInformation/getRoXmsVersion.ini"
  tar3="$WORK_DIR/bin/modfile/UpdateFile/Settings_ROMInformation/getXmsVersion.ini"
  tar4="$WORK_DIR/bin/modfile/UpdateFile/Settings_ROMInformation/getSimpleOSVersion.ini"
  my="$WORK_DIR/build/baserom/images/system/system/build.prop"
  final_version="${base_rom_code%.*}"
  simposcode="${final_version#OS}"

  mods "Updating getMiuiVersionInCard"
  $repS $tar1 $p1
  mods "Updating getRoXmsVersion"
  $repS $tar2 $p1
  mods "Updating getXmsVersion"
  $repS $tar3 $p1
  mods "Updating getSimpleOSVersionCode"
  $repS $tar4 $p1

  mods "Updating build.prop"
  echo "ro.deadzone.version=NothingsOS $myversion | $final_version" >> $my
  echo "ro.deadzone.osversion=${simposcode}.${build_date}" >> $my
  echo "ro.deadzone.simposcode=DeadZone By MEZO $myversion  " >> $my

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
  mods "Adding HyperOS Information Done!"

fi
