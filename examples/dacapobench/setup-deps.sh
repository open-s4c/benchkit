#!/bin/bash

mkdir -p deps
cd ./deps/

git clone git@github.com:dacapobench/dacapobench.git 
cp ../local.properties ./dacapobench/benchmarks/
