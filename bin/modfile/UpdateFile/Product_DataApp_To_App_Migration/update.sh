#!/bin/bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
work_dir="${WORK_DIR:-$(pwd)}"
if [[ ! -f "$work_dir/functions.sh" ]]; then
    work_dir="$(cd "$script_dir/../../../.." && pwd)"
fi

source "$work_dir/functions.sh"

info "Migrating product/data-app apps into product/app"
python3 "$script_dir/product_data_app_to_app_migration.py" --work-dir "$work_dir"
info "✅ Product data-app migration completed"
