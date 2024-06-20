.PHONY: all clean

buildDir=build

CC=gcc

SRCS=$(wildcard *.c)
BINS=$(SRCS:%.c=$(buildDir)/%)
all: $(BINS)
clean: 
	rm -f $(BINS)

$(buildDir)/%: %.c perfSwitch.h $(buildDir)/.f
	$(CC) -o $@ $< -O2 -lm

%/.f:
	mkdir -p $(dir $@)
	touch $@