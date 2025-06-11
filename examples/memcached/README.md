# memtier_benchmark



Original memtier_benchmark repository: https://github.com/RedisLabs/memtier_benchmark.git


# memcached



Original memcached repository: https://github.com/memcached/memcached.git


## Run the benchmark

```bash
mkdir deps/
cd deps/
git clone https://github.com/RedisLabs/memtier_benchmark.git
git clone https://github.com/memcached/memcached.git
cd ../
./configure.sh
./venv/bin/python3 campaign_memcached.py
```
