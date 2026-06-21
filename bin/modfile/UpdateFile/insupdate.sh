work_dir=$(pwd)
source "$work_dir/functions.sh"

mods "Starting Update File..."
TARGET_DIR="$work_dir/bin/modfile/UpdateFile"
ordered_mods=(
    "POCO_Launcher_Spoof"
    "Product_DataApp_To_App_Migration"
    "Provisions_DeadZone_Branding"
    "SystemUI_Hide_4G_Show_VoLTE"
)

run_update_script() {
    local script_path="$1"
    if [[ -f "$script_path" ]]; then
        bash "$script_path"
    fi
}

for mod_name in "${ordered_mods[@]}"; do
    run_update_script "$TARGET_DIR/$mod_name/update.sh"
done

find "$TARGET_DIR" -mindepth 2 -maxdepth 2 -type f -name "update.sh" | sort | while read -r script; do
    mod_name="$(basename "$(dirname "$script")")"
    skip=false
    for ordered in "${ordered_mods[@]}"; do
        if [[ "$mod_name" == "$ordered" ]]; then
            skip=true
            break
        fi
    done

    if [[ "$skip" == false ]]; then
        run_update_script "$script"
    fi
done
