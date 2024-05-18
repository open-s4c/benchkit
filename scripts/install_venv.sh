#!/bin/sh
set -e

venv_path=$1
[ -z "${venv_path}" ] && venv_path=venv

script_dir=$(dirname "$(readlink -f "$0")")

# dependencies: ${pythonex} ${pythonex}-venv ${pythonex}-dev

if python3 -c 'import sys; exit(0 if sys.version_info >= (3, 10) else 1)'
then
  # installed python is at least 3.10
  python_exec=python3
else
  # for earlier default, we force 3.10
  python_exec=python3.10
fi


${python_exec} -m venv ${venv_path}

pip_execs=$(find ${venv_path}/ -name "pip3*")
pip_exec=$(echo "${pip_execs}" | head -n 1)

${pip_exec} install --upgrade pip
${pip_exec} install --upgrade setuptools
${pip_exec} install --upgrade wheel
${pip_exec} install --upgrade pycodestyle isort pylint
${pip_exec} install --upgrade black black[d] black[jupyter]
${pip_exec} install --upgrade flake8

${pip_exec} install --upgrade "docopt<=0.6.2"
${pip_exec} install --upgrade "libtmux<=0.21.10"

requirement_file="requirements.txt"
if [ -e "${requirement_file}" ]
then
  ${pip_exec} install --upgrade --requirement "${requirement_file}"
else
  echo "No requirement file found, proceeding without installing any package." >&2
fi

"${script_dir}/add_paths_venv.sh" ${venv_path}
