//string format
//https://stackoverflow.com/a/35401865
//writing to file
//https://man.openbsd.org/write.2#EXAMPLES

#include <unistd.h>
#include <stdlib.h>
#include <assert.h>
#include <string.h>
#include <sys/types.h>
#include <sys/time.h>

#include <fcntl.h>
#include <unistd.h>
#include <limits.h>
#include <stdarg.h>

int perf_ctl_fd = 0;
int perf_ctl_ack_fd = 0;

struct timespec  realtime_before, realtime_after;
struct timespec  cpu_before, cpu_after;
double realtime_result, cpu_result;

void perfLib_exitWithMessage(char * format, ...) {
    va_list args;
    va_start(args,format);
    size_t nbytes = snprintf(NULL, 0, format, args) + 1; /* +1 for the '\0' */
    char *errStr = malloc(nbytes);
    snprintf(errStr, nbytes, format, args);
    perror(errStr);
    exit(EXIT_FAILURE);
}

//https://stackoverflow.com/a/68804612
double diff_timespec(struct timespec *time1, struct timespec *time0) {
  return (time1->tv_sec - time0->tv_sec)
         + (time1->tv_nsec - time0->tv_nsec) / 1000000000.0;
}

void perfLib_startRealTime() {
    if (clock_gettime(CLOCK_MONOTONIC, &realtime_before) == -1){
        perfLib_exitWithMessage("unable to use CLOCK_MONOTONIC\n");
    };
}

void perfLib_stopRealTime() {
    if (clock_gettime(CLOCK_MONOTONIC, &realtime_after) == -1){
        perfLib_exitWithMessage("unable to use CLOCK_MONOTONIC\n");
    };
    realtime_result = realtime_result + diff_timespec(&realtime_after,&realtime_before);
}

long int perfLib_reportRealTime() {
    return realtime_result * 1000000000;
}

void perfLib_startCPUTime() {
    if (clock_gettime(CLOCK_PROCESS_CPUTIME_ID, &cpu_before) == -1){
        perfLib_exitWithMessage("unable to use CLOCK_PROCESS_CPUTIME_ID\n");
    };
}
void perfLib_stopCPUTime() {
    if (clock_gettime(CLOCK_PROCESS_CPUTIME_ID, &cpu_after) == -1){
        perfLib_exitWithMessage("unable to use CLOCK_PROCESS_CPUTIME_ID\n");
    };
    cpu_result = cpu_result + diff_timespec(&cpu_before,&cpu_before);
}

long int perfLib_reportCPUTime() {
    return realtime_result * 1000000000;
}

void perfLib_startTimers() {
    perfLib_startCPUTime();
    perfLib_startRealTime();
}

void perfLib_stopTimers() {
    perfLib_stopCPUTime();
    perfLib_stopRealTime();
}

int perfLib_openAndClearFile(const char * path, mode_t mode) {
    int fileDescriptor = open(path,mode);
    if (fileDescriptor == -1) {
        perfLib_exitWithMessage("unable to open file %s:\n", path);
    }
    return fileDescriptor;
}

void perfLib_parseArgs(int argc, char* argv[]) {
  for (int i = 1; i < argc; i += 2) {
        if (!strcmp(argv[i], "--ctl_file")) {
            perf_ctl_fd = perfLib_openAndClearFile(argv[i + 1],O_WRONLY);
        } else if (!strcmp(argv[i], "--ctl_ack_file")) {
            perf_ctl_ack_fd = perfLib_openAndClearFile(argv[i + 1],O_RDONLY);
        }
    }
}

void perfLib_writeFileContents(int fileDescriptor,const char *content, size_t count) {
    ssize_t nw;
    for (int off = 0; off < count; off += nw)
	    if ((nw = write(fileDescriptor, content + off, count - off)) == 0 || nw == -1)
		    perfLib_exitWithMessage("unable return to write to file %i:\n", fileDescriptor);
}

void perfLib_waitForAck() {
    char ack[5];
    int s;
    for (int tries = 0; tries < 2; tries++){
	    if ((s = read(perf_ctl_ack_fd, ack, 5)) == -1 || strcmp(ack, "ack\n") != 0){
		    if (tries == 5){
                perfLib_exitWithMessage("Did not get an ack message in time %i:\n", perf_ctl_ack_fd);}
            sleep(2);
        }
    }
}

void perfLib_startPerf() {
    perfLib_writeFileContents(perf_ctl_fd, "enable\n", 8);
    //no ack file provided so we dont wait for it
    if (perf_ctl_ack_fd == 0) return;
    perfLib_waitForAck();
    perfLib_startTimers();
}

void perfLib_stopPerf() {
    perfLib_stopTimers();
    perfLib_writeFileContents(perf_ctl_fd, "disable\n", 9);
    //no ack file provided so we dont wait for it
    if (perf_ctl_ack_fd == 0) return;
    perfLib_waitForAck();
}


void __perfLib_clearFileContents(int fileDescriptor) {
    int success = ftruncate(fileDescriptor, 0);
    if (success == -1) {
        perfLib_exitWithMessage("unable to clear file %i:\n", fileDescriptor);
    }
}