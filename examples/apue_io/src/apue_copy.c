/*
 * APUE Figure 3.5 - copy stdin to stdout using read()/write().
 *
 * Compile with: gcc -O2 -Wall -DBUFFSIZE=4096 -o apue_copy apue_copy.c
 *
 * The program counts every successful read() call and prints the count
 * to stderr so that stdout can be redirected to /dev/null for timing.
 */

#include <unistd.h>
#include <stdio.h>

#ifndef BUFFSIZE
#error "BUFFSIZE must be defined at compile time via -DBUFFSIZE=N"
#endif

int main(void)
{
    char buf[BUFFSIZE];
    ssize_t n;
    unsigned long long loops = 0;

    while ((n = read(STDIN_FILENO, buf, BUFFSIZE)) > 0) {
        if (write(STDOUT_FILENO, buf, (size_t)n) != n) {
            perror("write error");
            return 1;
        }
        loops++;
    }

    if (n < 0) {
        perror("read error");
        return 1;
    }

    fprintf(stderr, "LOOPS=%llu\n", loops);
    return 0;
}
