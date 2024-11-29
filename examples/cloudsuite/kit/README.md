# Utilizing: Cloudsuite's web serving

## Clone faban repo

```bash
cd examples/cloudsuite/kit
mkdir deps
cd deps/

git clone https://github.com/akara/faban.git
cd faban

git checkout a3b7e011cf44f8aab86f8652d8959bfd93b066e3
git am ../../0001-Changes-to-faban-on-the-29-11.patch
git am ../../0002-Changes-faban-in-Nov-2024.patch

cd ..
cd ..
cd ../../../
```

## Generate fabandriver.jar

```bash
cd examples/cloudsuite/kit/deps/faban 

sudo apt install ant
sudo apt install openjdk-8-jdk openjdk-8-jre

java_path=$(find /usr/lib/jvm -name "java-1.8.0-op*")
export JAVA_HOME=$java_path
export JDK_HOME=$java_path
ant

cp driver/build/lib/fabandriver.jar ../../files/

cd ../../../../..
```
