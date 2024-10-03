#!/bin/bash

ctl_dir=/tmp/

mkdir -p ${ctl_dir}

ctl_fifo=${ctl_dir}perf_ctl.fifo
rm -if ${ctl_fifo}
touch ${ctl_fifo}

ctl_ack_fifo=${ctl_dir}perf_ctl_ack.fifo
rm -if ${ctl_ack_fifo}
touch ${ctl_ack_fifo}