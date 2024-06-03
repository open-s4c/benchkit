#!/bin/sh
set -e

if [ -d CppPathTracer ]
then
    cd CppPathTracer
    git pull
    cd ..
else
    git clone git@github.com:RobbeDGreef/CppPathTracer.git
fi

../../scripts/install_venv.sh
