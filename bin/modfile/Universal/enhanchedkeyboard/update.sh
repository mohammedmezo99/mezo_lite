work_dir=$(pwd)
source $work_dir/functions.sh
rom_os=$(cat $work_dir/bin/ddevice/rom_os.txt)
MAIN_FOLDER="$work_dir/build/baserom/images"
regionTYPE=$(cat $work_dir/bin/ddevice/device_type.txt) 
androidVER=$(cat $work_dir/bin/ddevice/androidver.txt)
APKEDITOR="java -jar $work_dir/bin/apktool/apke.jar"
repS="python3 $work_dir/bin/strRep.py"

if [[ $regionTYPE == "China" ]]; then
mods "Patching Enhanched Keyboard"
MOD_NAME="Enhanced Keyboard"
MIUIFrequentPhrase=$(find_apk_or_skip "$MOD_NAME" "MIUIFrequentPhrase.apk") || exit 0
MIUIFrequentPhraseDIR=$(dirname "$MIUIFrequentPhrase")
OUT_DIR="$work_dir/apk_temp/MIUIFrequentPhrase.apk.out"

if [ -n "$MIUIFrequentPhrase" ] && [ -f "$MIUIFrequentPhrase" ]; then
    mkdir -p $work_dir/apk_temp
    $APKEDITOR d -t raw -f -no-dex-debug -i "$MIUIFrequentPhrase" -o "$OUT_DIR" >/dev/null 2>&1 || true
    apk_out_exists_or_skip "$MOD_NAME" "$OUT_DIR" || { rm -rf "$work_dir/apk_temp"; exit 0; }
    Smali1=$(safe_find_smali "$MOD_NAME" "$OUT_DIR" "InputMethodBottomManager.smali") || { rm -rf "$work_dir/apk_temp"; exit 0; }
    if [ -n "$Smali1" ] && [ -f "$Smali1" ]; then
        sed -i 's/com.baidu.input_mi/com.google.android.inputmethod.latin/g' "$Smali1"
        #Finishing
        MIUIFrequentPhraseName=$(basename "$MIUIFrequentPhrase")
        $APKEDITOR b -f -i "$OUT_DIR" -o "$work_dir/apk_temp/final/$MIUIFrequentPhraseName" >/dev/null 2>&1

        if [ -f "$work_dir/apk_temp/final/$MIUIFrequentPhraseName" ]; then
            rm -rf "$MIUIFrequentPhraseDIR/oat"
            rm -rf "$MIUIFrequentPhraseDIR/$MIUIFrequentPhraseName"
            cp -rf "$work_dir/apk_temp/final/$MIUIFrequentPhraseName" "$MIUIFrequentPhraseDIR"
        fi
    else
        mods "InputMethodBottomManager.smali not found, skipping patch"
    fi
    rm -rf "$work_dir/apk_temp"
else
    mods "MIUIFrequentPhrase.apk not found, skipping patch"
fi
mods "Done"
fi
