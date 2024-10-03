//https://kuleuven-diepenbeek.github.io/osc-course/ch6-tasks/interthread/
//https://code-vault.net/lesson/j62v2novkv:1609958966824


#include <stdio.h>
#include <stdlib.h> 
#include <string.h>
#include <sys/time.h>
#include <time.h>
#include <math.h>
#include <pthread.h>
#include <semaphore.h>
#include <stdalign.h>
#include <unistd.h>


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

typedef struct args {
    int * field;
    char step;
    int startIndex;
} Args;

//https://stackoverflow.com/questions/14166350/how-to-display-a-matrix-in-c
void printMatrice(int* f) {
    int x = 0;
    int y = 0;

    for(x = 0 ; x < SIZE ; x++) {
        printf(" (");
        for(y = 0 ; y < SIZE ; y++){
            printf("%i|", f[x*SIZE * 2 + y * 2]);
        }
        printf(")\n");
    }
}

int somMatrice(int* f) {
    int x = 0;
    int y = 0;
    int r = 0;

    for(x = 0 ; x < SIZE ; x++) {
        for(y = 0 ; y < SIZE ; y++){
            r += f[x*SIZE * 2 + y * 2];
        }
    }
    return r;
}

int  transferAmount(int a, int b) {
    return (b - a) *  CHANGERATE;
}
    

void setupField(int * f) {
    for (int i = 0; i < SIZE*SIZE*2  ; i+=2){
        f[i] += (rand() % 8000);
    }
}

#define nextCellOffset 2
#define nextRowOffset 2 * SIZE

void updateLoop(void *input) {
    Args* catsted = input;
    int * field = catsted->field;
    char step = catsted->step;
    int startIndex = catsted->startIndex;
    int fromIndex;
    int toOfset;
    if (step) {
        fromIndex = startIndex + 1;
        toOfset = -1;
    } else {
        fromIndex = startIndex;
        toOfset = 1;
    }
    //check if is first line
    if (fromIndex < 2) {
        int initialValue = field[fromIndex];
        int newvalue = initialValue;
        newvalue += transferAmount(initialValue, field[fromIndex+nextCellOffset]);
        newvalue += transferAmount(initialValue, field[startIndex+nextRowOffset]);
        field[fromIndex + toOfset] = newvalue;

        for (int j = startIndex + nextCellOffset; j < startIndex + nextRowOffset - nextCellOffset; j+=2){
            initialValue = field[j];
            newvalue = initialValue;
            newvalue += transferAmount(initialValue, field[j+nextCellOffset]);
            newvalue += transferAmount(initialValue, field[j-nextCellOffset]);
            newvalue += transferAmount(initialValue, field[j+nextRowOffset]);
            field[j + toOfset] = newvalue;
        }

        //right side
        initialValue = field[startIndex+nextRowOffset-nextCellOffset];
        newvalue = initialValue;
        newvalue += transferAmount(initialValue, field[startIndex+nextRowOffset-nextCellOffset-nextCellOffset]);
        newvalue += transferAmount(initialValue, field[startIndex+nextRowOffset-nextCellOffset+nextRowOffset]);
        field[startIndex+nextRowOffset-nextCellOffset + toOfset] = newvalue;
        return;
    }
    //check if last line
    if (fromIndex > 2 * SIZE * (2 * SIZE - 1)) {
        int initialValue = field[fromIndex];
        int newvalue = initialValue;
        newvalue += transferAmount(initialValue, field[fromIndex+nextCellOffset]);
        newvalue += transferAmount(initialValue, field[startIndex-nextRowOffset]);
        field[startIndex + toOfset] = newvalue;

        for (int j = startIndex + nextCellOffset; j < startIndex + nextRowOffset - nextCellOffset; j+=2){
            initialValue = field[j];
            newvalue = initialValue;
            newvalue += transferAmount(initialValue, field[j+nextCellOffset]);
            newvalue += transferAmount(initialValue, field[j-nextCellOffset]);
            newvalue += transferAmount(initialValue, field[j-nextRowOffset]);
            field[j + toOfset] = newvalue;
        }

        //right side
        initialValue = field[startIndex+nextRowOffset-nextCellOffset];
        newvalue = initialValue;
        newvalue += transferAmount(initialValue, field[startIndex+nextRowOffset-nextCellOffset-nextCellOffset]);
        newvalue += transferAmount(initialValue, field[startIndex+nextRowOffset-nextCellOffset-nextRowOffset]);
        field[startIndex+nextRowOffset-nextCellOffset + toOfset] = newvalue;
        return;
    }

    //seperate the cases for first and last number
    //left side
    int initialValue = field[fromIndex];
    int newvalue = initialValue;
    newvalue += transferAmount(initialValue, field[fromIndex+nextCellOffset]);
    newvalue += transferAmount(initialValue, field[startIndex-nextRowOffset]);
    newvalue += transferAmount(initialValue, field[startIndex+nextRowOffset]);
    field[startIndex + toOfset] = newvalue;

    for (int j = startIndex + nextCellOffset; j < startIndex + nextRowOffset - nextCellOffset; j+=2){
        initialValue = field[j];
        newvalue = initialValue;
        newvalue += transferAmount(initialValue, field[j+nextCellOffset]);
        newvalue += transferAmount(initialValue, field[j-nextCellOffset]);
        newvalue += transferAmount(initialValue, field[j+nextRowOffset]);
        newvalue += transferAmount(initialValue, field[j-nextRowOffset]);
        field[j + toOfset] = newvalue;
    }

    //right side
    initialValue = field[startIndex+nextRowOffset-nextCellOffset];
    newvalue = initialValue;
    newvalue += transferAmount(initialValue, field[startIndex+nextRowOffset-nextCellOffset-nextCellOffset]);
    newvalue += transferAmount(initialValue, field[startIndex+nextRowOffset-nextCellOffset-nextRowOffset]);
    newvalue += transferAmount(initialValue, field[startIndex+nextRowOffset-nextCellOffset+nextRowOffset]);
    field[startIndex+nextRowOffset-nextCellOffset + toOfset] = newvalue;
}

Args taskQueue[255];
int taskStart = 0;
int taskEnd = 0;
int allTaskSubmitted = 0;

sem_t fill_count;

sem_t empty_count;

pthread_mutex_t mutexQueue;

pthread_barrier_t barrier;

void submitTask(Args task) {
    sem_wait(&empty_count );
    pthread_mutex_lock(&mutexQueue);
    taskQueue[taskEnd] = task;
    taskEnd = (taskEnd + 1) % 255;
    pthread_mutex_unlock(&mutexQueue);
    sem_post(&fill_count);
}

void* startThread(void* args) {
    while (1) {
        pthread_barrier_wait(&barrier);
        while (1) {
            Args task;

            sem_wait(&fill_count);
            pthread_mutex_lock(&mutexQueue);
            if ((taskStart==taskEnd))
            {
                pthread_mutex_unlock(&mutexQueue);
                goto roundDone;
            }

            task = taskQueue[taskStart];
            taskStart = (taskStart + 1) % 255;
            pthread_mutex_unlock(&mutexQueue);

            sem_post(&empty_count);
            updateLoop(&task);
        }
        roundDone:
        if (allTaskSubmitted){
                goto Done;
            }
    }
    Done:
}

int main(int argc, char* argv[]) {
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
  
    sem_init(&fill_count, 0, 0);
    sem_init(&empty_count, 0, 254);

    srand(SEED);

    alignas(64) int * field = calloc(SIZE*SIZE*2, sizeof(int));
    setupField(field);


    pthread_t th[THREADS];
    pthread_mutex_init(&mutexQueue, NULL);
    pthread_barrier_init(&barrier,NULL,THREADS + 1);
    int i;
    for (i = 0; i < THREADS; i++) {
        if (pthread_create(&th[i], NULL, &startThread, NULL) != 0) {
            perror("Failed to create the thread");
        }
    }


    perfLib_startPerf();

    char step = 0;
    int half = SIZE/2;
    for (int i = 0; i < ITERATIONS; i++)
    {
        pthread_barrier_wait(&barrier);

        for (int o = 0; o < 2; o++) {
            for (size_t j = 0; j < half; j++) {
            Args t = {
                .field = field,
                .step = step,
                .startIndex = (j * 2 + o) * SIZE * 2
            };
            submitTask(t);
            }
        }
        if (i == ITERATIONS - 1) {
            allTaskSubmitted = 1;
        }
        for (int p = 0; p < THREADS; p++) {
            sem_post(&fill_count);
        }
        step = !step;
    }
    for (i = 0; i < THREADS; i++) {
        if (pthread_join(th[i], NULL) != 0) {
            perror("Failed to join the thread");
        }
    }
    perfLib_stopPerf();
    printf("%ld\n", perfLib_reportRealTime());
    pthread_mutex_destroy(&mutexQueue);
    sem_destroy(&fill_count);
    sem_destroy(&empty_count);
    return 0;
}