# Campaign and Benchmark for nvJPEG_encoder

All source files taken from https://github.com/NVIDIA/cuda-samples/tree/master/Samples/4_CUDA_Libraries/nvJPEG_encoder

## Setting up the Python Virtual Environment
```
./configure.sh
source venv/bin/activate
```

## Set up the src directory
```
mkdir src && cd src
mkdir encode_output images
```

### Get the src code file and the cmake lists file
```wget https://raw.githubusercontent.com/NVIDIA/cuda-samples/refs/heads/master/Samples/4_CUDA_Libraries/nvJPEG_encoder/nvJPEG_encoder.cpp```
### Get the cmake lists file
```wget https://raw.githubusercontent.com/NVIDIA/cuda-samples/refs/heads/master/Samples/4_CUDA_Libraries/nvJPEG_encoder/CMakeLists.txt```

### You can download the images in the images directory from https://github.com/NVIDIA/cuda-samples/tree/master/Samples/4_CUDA_Libraries/nvJPEG_encoder/images
```
cd images
wget https://github.com/NVIDIA/cuda-samples/blob/master/Samples/4_CUDA_Libraries/nvJPEG_encoder/images/img1.jpg?raw=true \
    https://github.com/NVIDIA/cuda-samples/blob/master/Samples/4_CUDA_Libraries/nvJPEG_encoder/images/img2.jpg?raw=true \
    https://github.com/NVIDIA/cuda-samples/blob/master/Samples/4_CUDA_Libraries/nvJPEG_encoder/images/img3.jpg?raw=true \
    https://github.com/NVIDIA/cuda-samples/blob/master/Samples/4_CUDA_Libraries/nvJPEG_encoder/images/img4.jpg?raw=true \
    https://github.com/NVIDIA/cuda-samples/blob/master/Samples/4_CUDA_Libraries/nvJPEG_encoder/images/img5.jpg?raw=true \
    https://github.com/NVIDIA/cuda-samples/blob/master/Samples/4_CUDA_Libraries/nvJPEG_encoder/images/img6.jpg?raw=true \
    https://github.com/NVIDIA/cuda-samples/blob/master/Samples/4_CUDA_Libraries/nvJPEG_encoder/images/img7.jpg?raw=true \
    https://github.com/NVIDIA/cuda-samples/blob/master/Samples/4_CUDA_Libraries/nvJPEG_encoder/images/img8.jpg?raw=true
```
#### Rename the image files
```
for f in *?raw=true; do mv "$f" "${f%%?raw=true}"; done
cd ..
```

## Get the helper files
```
wget https://raw.githubusercontent.com/NVIDIA/cuda-samples/refs/heads/master/Common/helper_nvJPEG.hxx \
    https://raw.githubusercontent.com/NVIDIA/cuda-samples/refs/heads/master/Common/helper_string.h \
    https://raw.githubusercontent.com/NVIDIA/cuda-samples/refs/heads/master/Common/helper_timer.h \
    https://raw.githubusercontent.com/NVIDIA/cuda-samples/refs/heads/master/Common/exception.h \
    https://raw.githubusercontent.com/NVIDIA/cuda-samples/refs/heads/master/Common/helper_cuda.h \
    https://raw.githubusercontent.com/NVIDIA/cuda-samples/refs/heads/master/Common/helper_functions.h \
    https://raw.githubusercontent.com/NVIDIA/cuda-samples/refs/heads/master/Common/helper_image.h
```

### Edit Files
Edit the helper_cuda.h file by replacing line 41: <helper_string.h> with "helper_string.h"  
Edit the helper_timer.h file by replacing line 40: <exception.h> with "exception.h"  

### Exit the src directory
```cd ..```

## Running the campaigns
### Without the NCU wrapper
```python3 gpu_jpeg_encoder_campaign.py```
### With the NCU wrapper
```python3 gpu_jpeg_encoder_campaign_ncu.py```
