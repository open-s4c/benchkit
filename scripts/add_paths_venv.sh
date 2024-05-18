#!/bin/sh
set -e

venv_path=$1
[ -z "${venv_path}" ] && venv_path=venv

target_file=benchkit-dep.pth
venvsp_path=$(find ${venv_path}/lib -name 'site-packages' | head -n 1)

venv_rel_paths=""
if [ -e ./dependency-paths.txt ]
then
  while read -r rel_path
  do
    if [ -d "${rel_path}" ]
    then
      abs_path=$(readlink -e "${rel_path}")
      venv_rel_path=$(realpath --relative-to "${venvsp_path}" "${abs_path}")
      venv_rel_paths="${venv_rel_paths} ${venv_rel_path}"
    fi
  done < ./dependency-paths.txt
fi

(
  cd "${venvsp_path}"
  for path in ${venv_rel_paths}
  do
    echo "${path}" >> ${target_file}
  done
)
