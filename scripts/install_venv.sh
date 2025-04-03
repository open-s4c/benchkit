#!/bin/sh
set -e

this_dir="$(readlink -f "$(dirname "$0")")"
install_script="${this_dir}/install_venv.py"

python3 "${install_script}"
