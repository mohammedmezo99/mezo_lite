work_dir=$(pwd)
source $work_dir/functions.sh
MAIN_FOLDER="$work_dir/build/baserom/images"
repS="python3 $work_dir/bin/strRep.py"
deviceTYPE=$(cat $work_dir/bin/ddevice/device_type.txt)
androidVER=$(cat $work_dir/bin/ddevice/androidver.txt)
rom_os=$(cat $work_dir/bin/ddevice/rom_os.txt)
APKEDITOR="java -jar $work_dir/bin/apktool/apke.jar"
repS="python3 $work_dir/bin/strRep.py"

if [[ $rom_os == "OS3" || $rom_os == "OS2" || $rom_os == "OS1" ]]; then
MOD_NAME="Provisions Region Patch"
mods "Remove Region Check for HyperOS"
mkdir -p $work_dir/apk_temp
isProvision=$(find_apk_or_skip "$MOD_NAME" "Provision.apk") || exit 0
isProvisionDIR=$(dirname "$isProvision")
OUT_DIR="$work_dir/apk_temp/isProvision.apk.out"
$APKEDITOR d -t raw -f -no-dex-debug -i "$isProvision" -o "$OUT_DIR" >/dev/null 2>&1 || true
apk_out_exists_or_skip "$MOD_NAME" "$OUT_DIR" || { rm -rf "$work_dir/apk_temp"; exit 0; }
isMiuiProvisionSmali=$(safe_find_smali "$MOD_NAME" "$OUT_DIR" "Utils.smali") || { rm -rf "$work_dir/apk_temp"; exit 0; }
tar1="$work_dir/bin/modfile/UpdateFile/Provisions_RegionPatch/remove_regioncheck.ini"

$repS "$tar1" "$isMiuiProvisionSmali" >/dev/null 2>&1

#Finishing
Provision=$(basename "$isProvision")
$APKEDITOR b -f -i "$OUT_DIR" -o "$work_dir/apk_temp/final/$Provision" >/dev/null 2>&1

if [ -f "$work_dir/apk_temp/final/$Provision" ]; then
    rm -rf "$isProvisionDIR"/*
    cp -rf "$work_dir/apk_temp/final/$Provision" "$isProvisionDIR"
fi

rm -rf "$work_dir/apk_temp"
mods "Done"
fi
