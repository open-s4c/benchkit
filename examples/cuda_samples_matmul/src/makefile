# Compiler and flags
NVCC = nvcc
CFLAGS = -std=c++11

# Source and output
SRC = matrixMul.cu
OBJ = ../build/matrixMul.o
OUT =../build/matrixMul

# Include headers
INCLUDES = -I. # Ensure the headers are in the current directory

# Targets
all: $(OUT)

$(OUT): $(OBJ)
	$(NVCC) $(CFLAGS) $(OBJ) -o $(OUT)

$(OBJ): $(SRC) helper_functions.h helper_cuda.h helper_image.h helper_string.h helper_timer.h exception.h
	$(NVCC) $(CFLAGS) $(INCLUDES) -c $(SRC) -o $(OBJ)

clean:
	rm -f $(OBJ) $(OUT)

.PHONY: all clean
