#!/bin/bash
set -euo pipefail

work_dir=$(pwd)
source "$work_dir/functions.sh"

tmp_dir="$work_dir/out/validate_packaging"
rm -rf "$tmp_dir"
mkdir -p "$tmp_dir/bin/ddevice" "$tmp_dir/build/baserom/images" "$tmp_dir/bin/script2flash/META-INF/Data" "$tmp_dir/tools"
cp -f "$work_dir/functions.sh" "$tmp_dir/functions.sh"
cat > "$tmp_dir/tools/zstd" <<'EOF'
#!/bin/bash
set -euo pipefail
remove_input=0
input=""
output=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        --rm) remove_input=1 ;;
        -o)
            shift
            output="$1"
            ;;
        -f) ;;
        *)
            if [[ -z "$input" ]]; then
                input="$1"
            fi
            ;;
    esac
    shift
done

cp "$input" "$output"
if [[ "$remove_input" -eq 1 ]]; then
    rm -f "$input"
fi
EOF
chmod +x "$tmp_dir/tools/zstd"

printf '123\n' > "$tmp_dir/Version"
printf 'TAPASGlobal\n' > "$tmp_dir/bin/ddevice/device_code.txt"
printf 'tapas\n' > "$tmp_dir/bin/ddevice/device_f.txt"
printf 'OS3.0.2.0.WMGMIXM\n' > "$tmp_dir/bin/ddevice/base_rom_code.txt"
printf '16\n' > "$tmp_dir/bin/ddevice/androidver.txt"
printf 'Global\n' > "$tmp_dir/bin/ddevice/device_type.txt"
printf 'payload\n' > "$tmp_dir/bin/ddevice/romtype.txt"
printf 'placeholder\n' > "$tmp_dir/build/baserom/images/system.img"
printf 'device\n' > "$tmp_dir/bin/script2flash/META-INF/Data/DeviceCode"
printf 'region\n' > "$tmp_dir/bin/script2flash/META-INF/Data/Region"
printf 'bat\n' > "$tmp_dir/bin/script2flash/Windows_FastbootInstall.bat"
printf 'super\n' > "$tmp_dir/build/baserom/images/super.img"

if bash -n "$work_dir/packROM.sh"; then
    info "packROM.sh syntax OK"
fi

(
    cd "$tmp_dir"
    PATH="$tmp_dir/tools:$PATH" DEADZONE_DRY_RUN=1 bash "$work_dir/uploadROM.sh"
)

expected_name="DeadZoneLite_v123_TAPASGLOBAL_OS3.0.2.0.WMGMIXM_GlobalStable-A16.zip"
actual_name=$(< "$tmp_dir/bin/ddevice/output_zip.txt")
if [[ "$actual_name" != "$expected_name" ]]; then
    error "Unexpected final name: $actual_name"
    exit 1
fi

if [[ ! -f "$tmp_dir/out/$expected_name" ]]; then
    error "Final ZIP missing in dry-run validation"
    exit 1
fi

if [[ -f "$tmp_dir/out/package.zip" ]]; then
    error "package.zip should not be produced"
    exit 1
fi

if unzip -Z1 "$tmp_dir/out/$expected_name" | grep -q '^final_package/'; then
    error "ZIP unexpectedly contains a parent folder"
    exit 1
fi

info "Packaging dry-run validation passed"
