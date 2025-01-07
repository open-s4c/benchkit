# Cloudsuite's web serving

## Install required JVM packages

```bash
sudo apt-get update
sudo apt-get install -y ant openjdk-8-jdk openjdk-8-jre
```

## Clone faban repo

```bash
cd examples/cloudsuite/
mkdir deps/
cd deps/

git clone https://github.com/parsa-epfl/cloudsuite.git
cd cloudsuite/
git checkout c9d7584b9f4f0dec56e6683ebd61dad66ac1d06a
cd ../

git clone https://github.com/akara/faban.git
cd faban/
git checkout a3b7e011cf44f8aab86f8652d8959bfd93b066e3
git am ../../0001-faban-log-seed.patch
git am ../../0002-faban-log-thread-ops.patch

cd ../../../../
```

## Generate fabandriver.jar

```bash
cd examples/cloudsuite/deps/faban/

java_path=$(find /usr/lib/jvm -name "java-1.8.0-op*")
export JAVA_HOME=$java_path
export JDK_HOME=$java_path
ant

cp driver/build/lib/fabandriver.jar ../../kit/files/

cd ../../../..
```


## Run example campaign

```bash
cd examples/cloudsuite/
./campaign_cloudsuite.py
```
