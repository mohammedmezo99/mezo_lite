work_dir=$(pwd)
source $work_dir/functions.sh
MAIN_FOLDER="$work_dir/build/baserom/images"
repS="python3 $work_dir/bin/strRep.py"
deviceTYPE=$(cat $work_dir/bin/ddevice/device_type.txt)
androidVER=$(cat $work_dir/bin/ddevice/androidver.txt)
rom_os=$(cat $work_dir/bin/ddevice/rom_os.txt)
APKEDITOR="java -jar $work_dir/bin/apktool/apke.jar"
repS="python3 $work_dir/bin/strRep.py"



if [[ $rom_os == "OS1" || $rom_os == "OS2" || $rom_os == "OS3" ]]; then
MOD_NAME="SystemUI Notification Color Icon"
mods "Patching ColorIcon SystemUI"
mkdir -p $work_dir/apk_temp
isMiuiSystemUI=$(find_apk_or_skip "$MOD_NAME" "MiuiSystemUI.apk") || exit 0
isMiuiSystemUIDIR=$(dirname "$isMiuiSystemUI")
OUT_DIR="$work_dir/apk_temp/isMiuiSystemUI.apk.out"
$APKEDITOR d -t raw -f -no-dex-debug -i "$isMiuiSystemUI" -o "$OUT_DIR" >/dev/null 2>&1 || true
apk_out_exists_or_skip "$MOD_NAME" "$OUT_DIR" || { rm -rf "$work_dir/apk_temp"; exit 0; }
Smali1=$(safe_find_smali "$MOD_NAME" "$OUT_DIR" "MiuiConfigs.smali") || { rm -rf "$work_dir/apk_temp"; exit 0; }
sed -i 's/"_global"/""/g' "$Smali1"
#Finishing
MiuiSystemUI=$(basename "$isMiuiSystemUI")
$APKEDITOR b -f -i "$OUT_DIR" -o "$work_dir/apk_temp/final/$MiuiSystemUI" >/dev/null 2>&1

if [ -f "$work_dir/apk_temp/final/$MiuiSystemUI" ]; then
    rm -rf "$isMiuiSystemUIDIR/oat"
	rm -rf "$isMiuiSystemUIDIR/$MiuiSystemUI"
    cp -rf "$work_dir/apk_temp/final/$MiuiSystemUI" "$isMiuiSystemUIDIR"
fi

rm -rf "$work_dir/apk_temp"
mods "Done"

fi
