#include <stdio.h>
#include <stdlib.h> 
#include <string.h>
#include <time.h>
#include <math.h>
#include <pthread.h>
#include <sys/time.h>
#include <unistd.h>
#include <assert.h>

#include "perfSwitch.h"



 #define max(a,b) \
   ({ __typeof__ (a) _a = (a); \
       __typeof__ (b) _b = (b); \
     _a > _b ? _a : _b; })

 #define min(a,b) \
   ({ __typeof__ (a) _a = (a); \
       __typeof__ (b) _b = (b); \
     _a < _b ? _a : _b; })


int SIZE = 0, 
    ITERATIONS = 0,
    THREADS = 1,
    SEED;

float CHANGERATE = 0.24;


//https://stackoverflow.com/questions/14166350/how-to-display-a-matrix-in-c
void printMatrice(int** f) {
    int x = 0;
    int y = 0;

    for(x = 0 ; x < SIZE ; x++) {
        printf(" (");
        for(y = 0 ; y < SIZE ; y++){
            printf("%i|", f[x][y]);
        }
        printf(")\n");
    }
}

int somMatrice(int** f) {
    int x = 0;
    int y = 0;
    int r = 0;

    for(x = 0 ; x < SIZE ; x++) {
        for(y = 0 ; y < SIZE ; y++){
            r += f[x][y];
        }
    }
    return r;
}

int  transferAmount(int a, int b) {
    return (b - a) *  CHANGERATE;
}

typedef struct args {
    int ** from;
    int ** to;
    char step;
    int lineNumber;
} Args;

void* updateLoop(void *input) {
    Args* catsted = input;
    int ** from = catsted->from;
    int ** to = catsted->to;
    char step = catsted->step;
    int lineNumber = catsted->lineNumber;


    if (step)
    {
        int** temp = from;
        from = to;
        to = temp;
    }
    

    for (int j = 0; j < SIZE; j++){
        int v = from[lineNumber][j];
        to[lineNumber][j] = v;
        if (lineNumber < SIZE - 1)
        {
            to[lineNumber][j] += transferAmount(v, from[lineNumber+1][j]);
        }
        if (lineNumber > 0)
        {
            to[lineNumber][j] += transferAmount(v, from[lineNumber-1][j]);
        }
        if (j < SIZE - 1)
        {
            to[lineNumber][j] += transferAmount(v, from[lineNumber][j+1]);
        }
        if (j > 0)
        {
            to[lineNumber][j] += transferAmount(v, from[lineNumber][j-1]);
        }
    }
}

void setupField(int ** f) {
    int res = pow((double)SIZE,2);
    for (int i = 0; i < SIZE  ; i++){
        for (int j = 0; j < SIZE  ; j++){
        f[i][j] += (rand() % 8000);
        }
    }
}


int main(int argc, char *argv[]) {
    perfLib_parseArgs(argc,argv);
    SEED = time(0);
    for (int i = 1; i < argc; i += 2) {
        if (!strcmp(argv[i], "-s")) {
            SIZE = atoi(argv[i + 1]);
        } else if (!strcmp(argv[i], "-i")) {
            ITERATIONS = atoi(argv[i + 1]);
        } else if (!strcmp(argv[i], "-seed")) {
            SEED = atoi(argv[i + 1]);
        } else if (!strcmp(argv[i], "-t")) {
            THREADS = atoi(argv[i + 1]);
        }
    }

    srand (SEED);

    int ** field1 = calloc(SIZE, sizeof(int *));
    for (int i = 0; i < SIZE; i++)
    {
        field1[i] = (int *) calloc(SIZE, sizeof(int));
    }
    int ** field2 = calloc(SIZE, sizeof(int *));
    for (int i = 0; i < SIZE; i++)
    {
        field2[i] = (int *) calloc(SIZE, sizeof(int));
    }
    int ** fieldinput = calloc(SIZE, sizeof(int *));
    setupField(field1);
    char step = 0;

    perfLib_startPerf();
    pthread_t threads[THREADS];
    Args thread_args[THREADS];


    for (int i = 0; i < ITERATIONS; i++)
    {
        int remainingLines = SIZE;
        while (remainingLines > 0){
            int r = min(THREADS,remainingLines);
            for (size_t t = 0; t < r; t++){

                Args *arg = &thread_args[t];
                arg->from = field1;
                arg->to = field2;
                arg->step = step;
                arg->lineNumber = (remainingLines - 1 - t);

                //updateLoop(&thread_args[t]);
                pthread_create(&threads[t], NULL, updateLoop, &thread_args[t]);
            };
            for (size_t t = 0; t < r; t++){
                pthread_join(threads[t],NULL);
            };
            remainingLines -= r;

        }
        step = !step;
    }
    perfLib_stopPerf();
    printf("%ld\n", perfLib_reportRealTime());

    somMatrice(field1);
    return 0;
}
