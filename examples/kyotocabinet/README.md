# Example: Kyoto Cabinet

## Clone Kyoto Cabinet repo

```bash
cd examples/kyotocabinet/
mkdir deps
cd deps/
wget --continue https://dbmx.net/kyotocabinet/pkg/kyotocabinet-1.2.76.tar.gz
tar -xf kyotocabinet-1.2.76.tar.gz
cd kyotocabinet-1.2.76/
git init && git add -A && git commit -m "Vanilla 1.2.76"
git apply ../../patch01-cloudflare.diff && git add -A && git commit -m "Cloudflare"
git apply ../../patch02-cloudflare.diff && git add -A && git commit -m "Cloudflare (new files)"
git apply ../../patch03-benchmark.diff && git add -A && git commit -m "Add benchmark"
git apply ../../patch04-benchkit.diff && git add -A && git commit -m "Benchkit glue"
cd ../../../..
```

## Generate venv & configure it

```bash
cd examples/kyotocabinet/
./configure.sh
cd ../..
```

## Run campaign for Kyoto Cabinet benchmarks

```bash
cd examples/kyotocabinet/
. ./venv/bin/activate
./campaign_Kyoto Cabinet.py
```
