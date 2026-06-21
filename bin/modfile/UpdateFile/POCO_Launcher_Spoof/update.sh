#!/bin/bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
work_dir="${WORK_DIR:-$(pwd)}"
if [[ ! -f "$work_dir/functions.sh" ]]; then
    work_dir="$(cd "$script_dir/../../../.." && pwd)"
fi

source "$work_dir/functions.sh"

info "Applying POCO launcher spoof"
python3 "$script_dir/poco_launcher_spoof.py" --work-dir "$work_dir"
info "✅ POCO launcher spoof completed"
