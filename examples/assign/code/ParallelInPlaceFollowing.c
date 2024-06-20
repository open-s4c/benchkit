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
    SEED,
    LOCKSPERROW = 1;

float CHANGERATE = 0.24;

typedef struct args {
    int * field;
} Args;

//https://stackoverflow.com/questions/14166350/how-to-display-a-matrix-in-c
void printMatrice(int* f) {
    int x = 0;
    int y = 0;

    for(x = 0 ; x < SIZE ; x++) {
        printf(" (");
        for(y = 0 ; y < SIZE ; y++){
            printf("%i|", f[x*SIZE + y]);
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
            r += f[x*SIZE + y];
        }
    }
    return r;
}

int  transferAmount(int a, int b) {
    return (b - a) *  CHANGERATE;
}
    

void setupField(int * f) {
    for (int i = 0; i < SIZE*SIZE  ; i++){
        f[i] += (rand() % 8000);
    }
}

alignas(64) pthread_mutex_t * locksArray;

void* updateLoop(void * input,int * oldPointer) {
    Args* catsted = input;
    int * field = catsted->field;
    int blocksize = SIZE/LOCKSPERROW;

    //--------------------------------------------
    //first line
    //--------------------------------------------
    //left side
    int rowstart = 0;

    pthread_mutex_lock(&locksArray[0]);

    int initialValue = field[rowstart];
    int newvalue = initialValue;
    newvalue += transferAmount(initialValue, field[rowstart+1]);
    newvalue += transferAmount(initialValue, field[rowstart+SIZE]);
    oldPointer[0] = initialValue;
    field[0] = newvalue;

    //middle
    int j = 1;
    for (int l = 1; l < LOCKSPERROW; l++){
        pthread_mutex_lock(&locksArray[l]);
        int endVal;
        if(l == LOCKSPERROW - 1){
            endVal = SIZE - 1;
        } else { endVal = l * blocksize; }
        for (; j < endVal; j++){
            int index = rowstart + j;
            initialValue = field[index];
            newvalue = initialValue;
            newvalue += transferAmount(initialValue, field[index+1]);
            newvalue += transferAmount(initialValue, oldPointer[j-1]);
            newvalue += transferAmount(initialValue, field[index+SIZE]);
            oldPointer[j] = initialValue;
            field[index] = newvalue;
        }
    }

    //right side
    int index = rowstart+SIZE-1;
    initialValue = field[rowstart+SIZE-1];
    newvalue = initialValue;
    newvalue += transferAmount(initialValue, field[index + SIZE]);
    newvalue += transferAmount(initialValue, oldPointer[SIZE - 1 - 1]);
    oldPointer[SIZE-1] = initialValue;
    field[index] = newvalue;
    //--------------------------------------------
    //middle lines
    //--------------------------------------------

    //--------------------------------------------
    //-------first middle line
    //--------------------------------------------

    //leftside
    rowstart = SIZE;

    pthread_mutex_lock(&locksArray[LOCKSPERROW]);

    initialValue = field[rowstart];
    newvalue = initialValue;
    newvalue += transferAmount(initialValue, field[rowstart+1]);
    newvalue += transferAmount(initialValue, field[rowstart+SIZE]);
    newvalue += transferAmount(initialValue, oldPointer[0]);
    oldPointer[0] = initialValue;
    field[rowstart] = newvalue;
    j = 1;
    for (int l = 1; l < LOCKSPERROW; l++){
        pthread_mutex_lock(&locksArray[LOCKSPERROW + l]);
        pthread_mutex_unlock(&locksArray[-1 + l]);
        int endVal;
        if(l == LOCKSPERROW - 1){
            endVal = SIZE - 1;
        } else { endVal = l * blocksize; }
        for (; j < endVal; j++){
            int index = rowstart + j;
            initialValue = field[index];
            newvalue = initialValue;
            newvalue += transferAmount(initialValue, field[index+1]);
            newvalue += transferAmount(initialValue, oldPointer[j-1]);
            newvalue += transferAmount(initialValue, field[index+SIZE]);
            newvalue += transferAmount(initialValue, oldPointer[j]);
            oldPointer[j] = initialValue;
            field[index] = newvalue;
        }
    }
    //right side
    index = rowstart+SIZE-1;
    initialValue = field[index];
    newvalue = initialValue;
    newvalue += transferAmount(initialValue, field[index + SIZE]);
    newvalue += transferAmount(initialValue, oldPointer[SIZE -1]);
    newvalue += transferAmount(initialValue, oldPointer[SIZE -1 - 1]);
    oldPointer[SIZE-1] = initialValue;
    field[index] = newvalue;

    //--------------------------------------------
    //-------all other middle lines
    //--------------------------------------------

    for(int i =  2 ; i < SIZE - 1 ; i ++) {
        //leftside
        int rowstart = i * SIZE;

        pthread_mutex_lock(&locksArray[i*LOCKSPERROW]);
        pthread_mutex_unlock(&locksArray[(i-1)*LOCKSPERROW - 1]);

        int initialValue = field[rowstart];
        int newvalue = initialValue;
        newvalue += transferAmount(initialValue, field[rowstart+1]);
        newvalue += transferAmount(initialValue, field[rowstart+SIZE]);
        newvalue += transferAmount(initialValue, oldPointer[0]);
        oldPointer[0] = initialValue;
        field[rowstart] = newvalue;
        int j = 1;
        for (int l = 1; l < LOCKSPERROW; l++){
            pthread_mutex_lock(&locksArray[i*LOCKSPERROW + l]);
            pthread_mutex_unlock(&locksArray[(i-1)*LOCKSPERROW - 1 + l]);
            int endVal;
            if(l == LOCKSPERROW - 1){
                endVal = SIZE - 1;
            } else { endVal = l * blocksize; }
            for (; j < endVal; j++){
                int index = rowstart + j;
                initialValue = field[index];
                newvalue = initialValue;
                newvalue += transferAmount(initialValue, field[index+1]);
                newvalue += transferAmount(initialValue, oldPointer[j-1]);
                newvalue += transferAmount(initialValue, field[index+SIZE]);
                newvalue += transferAmount(initialValue, oldPointer[j]);
                oldPointer[j] = initialValue;
                field[index] = newvalue;
            }
        }
        //right side
        int index = rowstart+SIZE-1;
        initialValue = field[index];
        newvalue = initialValue;
        newvalue += transferAmount(initialValue, field[index + SIZE]);
        newvalue += transferAmount(initialValue, oldPointer[SIZE -1]);
        newvalue += transferAmount(initialValue, oldPointer[SIZE -1 - 1]);
        oldPointer[SIZE-1] = initialValue;
        field[index] = newvalue;
    }
    //--------------------------------------------
    //last line
    //--------------------------------------------
    //leftside
    rowstart = (SIZE - 1) * SIZE;
    pthread_mutex_unlock(&locksArray[(SIZE-1-1)*LOCKSPERROW - 1]);

    initialValue = field[rowstart];
    newvalue = initialValue;
    newvalue += transferAmount(initialValue, field[rowstart+1]);
    newvalue += transferAmount(initialValue, oldPointer[0]);
    oldPointer[0] = initialValue;
    field[rowstart] = newvalue;
    j = 1;
    for (int l = 1; l < LOCKSPERROW; l++){
        pthread_mutex_unlock(&locksArray[(SIZE-1-1)*LOCKSPERROW - 1 + l]);
        int endVal;
        if(l == LOCKSPERROW - 1){
            endVal = SIZE - 1;
        } else { endVal = l * blocksize; }
        for (; j < endVal; j++){
            int index = rowstart + j;
            initialValue = field[index];
            newvalue = initialValue;
            newvalue += transferAmount(initialValue, field[index+1]);
            newvalue += transferAmount(initialValue, oldPointer[j-1]);
            newvalue += transferAmount(initialValue, oldPointer[j]);
            oldPointer[j] = initialValue;
            field[index] = newvalue;
        }
    }
    //right side
    index = rowstart+SIZE-1;
    initialValue = field[rowstart+SIZE-1];
    newvalue = initialValue;
    newvalue += transferAmount(initialValue, oldPointer[SIZE -1]);
    newvalue += transferAmount(initialValue, oldPointer[SIZE -1 - 1]);
    field[index] = newvalue;
    pthread_mutex_unlock(&locksArray[(SIZE-1)*LOCKSPERROW - 1]);
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
    alignas(64) int * oldPointer = calloc(SIZE, sizeof(int));
    while (1) {
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
            updateLoop(&task,oldPointer);
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
        } else if (!strcmp(argv[i], "-l")) {
            LOCKSPERROW = atoi(argv[i + 1]);
        }
    }
    if (LOCKSPERROW < 2)
    {
        printf("needs at least a LOCKSPERROW of 2"); exit(EXIT_FAILURE);
    }
  
    sem_init(&fill_count, 0, 0);
    sem_init(&empty_count, 0, 254);

    srand(SEED);

    alignas(64) int * field = calloc(SIZE*SIZE, sizeof(int));
    locksArray = calloc(SIZE*LOCKSPERROW, sizeof(pthread_mutex_t));
    for (int i = 0; i < (SIZE - 1) * LOCKSPERROW; i++) {
        pthread_mutex_init(&locksArray[i], NULL);
    }
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

    for (int i = 0; i < ITERATIONS; i++)
    {
        Args t = {
            .field = field
        };
        submitTask(t);
    }
    allTaskSubmitted = 1;
    for (int p = 0; p < THREADS; p++) {
        sem_post(&fill_count);
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