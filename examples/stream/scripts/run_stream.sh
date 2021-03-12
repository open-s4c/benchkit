#!/bin/bash


N=$1
dateval=$(date -u '+%Y%m%d_%H%M%S')
kernel=$(uname -r | cut -d'-' -f 3)

nb_threads="4 6 12"
iterations="1 2 3"

prepare_output() {
	raw_output=$1
	copy=$(echo "${raw_output}" | grep -o "Copy: *[0-9.]\+" | xargs | cut -d' ' -f 2)
	copy2=$(echo "${raw_output}" | grep -o "Copy: *[0-9.]\+ *[0-9.]\+" | xargs | cut -d' ' -f 3)
	scale=$(echo "${raw_output}" | grep -o "Scale: *[0-9.]\+" | xargs | cut -d' ' -f 2)
	scale2=$(echo "${raw_output}" | grep -o "Scale: *[0-9.]\+ *[0-9.]\+" | xargs | cut -d' ' -f 3)
	add=$(echo "${raw_output}" | grep -o "Add: *[0-9.]\+" | xargs | cut -d' ' -f 2)
	add2=$(echo "${raw_output}" | grep -o "Add: *[0-9.]\+ *[0-9.]\+" | xargs | cut -d' ' -f 3)
	triad=$(echo "${raw_output}" | grep -o "Triad: *[0-9.]\+" | xargs | cut -d' ' -f 2)
	triad2=$(echo "${raw_output}" | grep -o "Triad: *[0-9.]\+ *[0-9.]\+" | xargs | cut -d' ' -f 3)
}

output_file="stream_${dateval}_N${N}_Kernel${kernel}-cluster.csv"
echo "kernel;array_size;nb_threads;iteration;taskset;copy-maxrate;copy-avgtime;scale-maxrate;scale-avgtime;add-maxrate;add-avgtime;triad-maxrate;triad-avgtime" > ${output_file}

for it in ${iterations}
do
	for nb in ${nb_threads}
	do
		echo "Running ${nb}-threads test"
		echo "Limited to the first NUMA"

		raw_output=$(OMP_NUM_THREADS=${nb} taskset --cpu-list 0-23 ./stream_c.exe 2>&1)
		prepare_output "${raw_output}"
		echo "${kernel}-cluster;${N};${it};${nb};yes;${copy};${copy2};${scale};${scale2};${add};${add2};${triad};${triad2}" >> ${output_file}

		echo "Can run in the entire system"

		raw_output=$(OMP_NUM_THREADS=${nb} ./stream_c.exe 2>&1)
		prepare_output "${raw_output}"
		echo "${kernel}-cluster;${N};${it};${nb};no;${copy};${copy2};${scale};${scale2};${add};${add2};${triad};${triad2}" >> ${output_file}
	done
done
