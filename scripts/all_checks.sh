#!/bin/sh
set -e

script_dir=$(readlink -e "$(dirname "$0")")
benchkit_root_dir=$(readlink -e "${script_dir}/..")
venv_dir=$(readlink -f "${benchkit_root_dir}/venv")

(
  cd "${benchkit_root_dir}"

  if [ ! -d "${venv_dir}" ]
  then
    echo "-- venv in root dir of benchkit not present. Creating one. --"
    cat > ./requirements.txt << EOF
altair<=5.1.1
dash<=2.13.0
GitPython<=3.1.36
matplotlib<=3.8.0
netifaces<=0.11.0
pandas<=2.1.0
pythainer
seaborn<=0.12.2
wget<=3.2
EOF
    cat > ./dependency-paths.txt << EOF
.
examples/benchmarksql/kit
examples/kyotocabinet/kit
examples/leveldb/kit
examples/locktorture/kit
examples/mysql/kit
examples/postgresql/kit
examples/rocksdb/kit
examples/stream/kit
examples/sysbench/kit
examples/willitscale/kit
tutorials/libvsync-locks/kit
EOF
    ./scripts/install_venv.sh
    pip=$(readlink -f "${venv_dir}/bin/pip3")
    rm ./requirements.txt ./dependency-paths.txt
    echo "-- venv created. --"
  fi

  py3=$(readlink -f "${venv_dir}/bin/python3")
  pylint=$(readlink -f "${venv_dir}/bin/pylint")
  flake8=$(readlink -f "${venv_dir}/bin/flake8")
  isort=$(readlink -f "${venv_dir}/bin/isort")
  black=$(readlink -f "${venv_dir}/bin/black")

  echo "-- check copyright. --"
  ${py3} ./scripts/list_missing_copyright.py

  echo "-- running pylint. --"
  ${pylint} benchkit/ examples/ plotbench/src/ scripts/ tests/ tutorials/ || true

  echo "-- running flake8. --"
  ${flake8} benchkit/ examples/ plotbench/src/ scripts/ tests/ tutorials/ || true

  echo "-- running isort. --"
  ${isort} --profile=black benchkit/ examples/ plotbench/src/ scripts/ tests/ tutorials/

  echo "-- running black. --"
  ${black} -l 100 .
)
