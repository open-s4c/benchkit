#!/bin/sh
set -e

npb_version=3.4.3

script_dir=$(readlink -e "$(dirname "$0")")
deps_dir=${script_dir}/deps

mkdir -p "${deps_dir}"
cd "${deps_dir}"

# Download and extract the standard NPB
if [ ! -d npb ]; then
  wget --continue "https://www.nas.nasa.gov/assets/npb/NPB${npb_version}.tar.gz"
  tar -xf "NPB${npb_version}.tar.gz" && rm "NPB${npb_version}.tar.gz"
  mv "NPB${npb_version}" npb
  cd npb
  git init && git add -A && git commit -m "Vanilla NPB ${npb_version}"
  cd ..
fi

# Download and extract the NPB-MZ
if [ ! -d npb-mz ]; then
  wget --continue "https://www.nas.nasa.gov/assets/npb/NPB${npb_version}-MZ.tar.gz"
  tar -xf "NPB${npb_version}-MZ.tar.gz" && rm "NPB${npb_version}-MZ.tar.gz"
  mv "NPB${npb_version}-MZ" npb-mz
  cd npb-mz
  git init && git add -A && git commit -m "Vanilla NPB-MZ ${npb_version}"
  cd ..
fi
