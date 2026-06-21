#!/bin/bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
work_dir="${WORK_DIR:-$(pwd)}"
if [[ ! -f "$work_dir/functions.sh" ]]; then
    work_dir="$(cd "$script_dir/../../../.." && pwd)"
fi

source "$work_dir/functions.sh"

info "Patching Provision DeadZone branding strings"
python3 "$script_dir/provisions_deadzone_branding.py" --work-dir "$work_dir"
info "✅ Provision DeadZone branding completed"
