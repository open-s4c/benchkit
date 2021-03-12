#!/bin/sh
set -e

pycampaign=$@

if [ ! -d venv ] || [ "x${VIRTUAL_ENV}x" != "x$(readlink -e venv)x" ]
then
  # Get paths into python path if there is no venv
  rel_paths=${rel_paths}

  abs_paths=""
  while read -r rel_path
  do
    if [ -d "${rel_path}" ]
    then
      abs_path=$(readlink -f "${rel_path}")
      abs_paths="${abs_paths} ${abs_path}"
    fi
  done < ./dependency-paths.txt
  paths=$(echo "${abs_paths}" | xargs | sed "s/ /:/g")
  export PYTHONPATH=${paths}
fi

./${pycampaign}
