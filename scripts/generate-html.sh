#!/bin/sh
set -e

notebooks=$@

[ -z "${notebooks}" ] && notebooks=$(find . -maxdepth 1 -name '*.ipynb')

for notebook in ${notebooks}
do
  echo "-- Generating rendered html for '${notebook}' --"
  ./venv/bin/jupyter nbconvert \
    --execute \
    --no-input \
    --to html \
    --output-dir=rendered \
    "${notebook}"
done
