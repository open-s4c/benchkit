# Campaign and Benchmark for nvJPEG_encoder

All source files taken from https://github.com/NVIDIA/cuda-samples/tree/master/Samples/0_Introduction/matrixMul

## Setting up the Python environment
```
./configure.sh
source venv/bin/activate
```

## Setting up the src directory
```cd src```

## Get the files
```
wget https://raw.githubusercontent.com/NVIDIA/cuda-samples/refs/heads/master/Samples/0_Introduction/matrixMul/matrixMul.cu
wget https://raw.githubusercontent.com/NVIDIA/cuda-samples/refs/heads/master/Common/helper_string.h \
    https://raw.githubusercontent.com/NVIDIA/cuda-samples/refs/heads/master/Common/helper_timer.h \
    https://raw.githubusercontent.com/NVIDIA/cuda-samples/refs/heads/master/Common/exception.h \
    https://raw.githubusercontent.com/NVIDIA/cuda-samples/refs/heads/master/Common/helper_cuda.h \
    https://raw.githubusercontent.com/NVIDIA/cuda-samples/refs/heads/master/Common/helper_functions.h \
    https://raw.githubusercontent.com/NVIDIA/cuda-samples/refs/heads/master/Common/helper_image.h
cd ..
```


## Running the campaigns
```python3 matrixmul_campaign.py```
### matrixmul_campaign_ncu.py is the same campaign using the NCU wrapper
