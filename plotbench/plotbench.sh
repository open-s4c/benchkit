#!/bin/sh
set -e

script_dir=$(readlink -e "$(dirname "$0")")
py3=${script_dir}/venv/bin/python3
webapp=${script_dir}/src/webapp.py
cur_dir=${PWD}

(
  cd "${script_dir}"
  ${py3} "${webapp}" "${cur_dir}"
)
