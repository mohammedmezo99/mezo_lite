#!/bin/bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
work_dir="${WORK_DIR:-$(pwd)}"
if [[ ! -f "$work_dir/functions.sh" ]]; then
    work_dir="$(cd "$script_dir/../../../.." && pwd)"
fi

source "$work_dir/functions.sh"

info "Patching SystemUI hide 4G / show VoLTE"
python3 "$script_dir/systemui_hide_4g_show_volte.py" --work-dir "$work_dir"
info "✅ SystemUI Hide 4G / Show VoLTE completed"
