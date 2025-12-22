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

if ! which ${python_exec} > /dev/null
then
  echo "The right Python version (${python_exec}) for the benchmark is not installed on the system." >&2
  echo "On Ubuntu, you need to install the following packages: ${python_exec} ${python_exec}-venv ${python_exec}-dev" >&2
  exit 1
fi

${python_exec} -m venv ${venv_path}
python_exec=${venv_path}/bin/${python_exec}

pip_execs=$(find "${venv_path}/" -name "pip3*")
pip_exec=$(echo "${pip_execs}" | head -n 1)

${pip_exec} install --upgrade pip
${pip_exec} install --upgrade setuptools
${pip_exec} install --upgrade wheel

${pip_exec} install --upgrade \
    "black<=25.12.0" \
    "black[d]<=25.12.0" \
    "black[jupyter]<=25.12.0" \
    "docopt<=0.6.2" \
    "flake8<=7.3.0" \
    "isort<=7.0.0" \
    "libtmux<=0.53.0" \
    "mypy<=1.19.1" \
    "pycodestyle<=2.14.0" \
    "pylint<=4.0.4" \
    "rich<=14.2.0"

requirement_file="requirements.txt"
if [ -e "${requirement_file}" ]
then
  ${pip_exec} install --upgrade --requirement "${requirement_file}"
else
  echo "No requirement file found, proceeding without installing any package." >&2
fi

"${python_exec}" "${script_dir}/add_paths_venv.py" ${venv_path}
