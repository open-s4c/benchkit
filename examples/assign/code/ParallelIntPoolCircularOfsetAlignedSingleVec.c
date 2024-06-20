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
    int * from;
    int * to;
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


void* updateLoop(void *input) {
    Args* catsted = input;
    int * from = catsted->from;
    int * to = catsted->to;
    char step = catsted->step;
    int startIndex = catsted->startIndex;

    if (step)
    {
        int* temp = from;
        from = to;
        to = temp;
    }
    //check if is first line
    if (startIndex == 0) {
        int initialValue = from[startIndex];
        int newvalue = initialValue;
        newvalue += transferAmount(initialValue, from[startIndex+1]);
        newvalue += transferAmount(initialValue, from[startIndex+SIZE]);
        to[startIndex] = newvalue;

        for (int j = startIndex + 1; j < startIndex + SIZE - 1; j++){
            initialValue = from[j];
            newvalue = initialValue;
            newvalue += transferAmount(initialValue, from[j+1]);
            newvalue += transferAmount(initialValue, from[j-1]);
            newvalue += transferAmount(initialValue, from[j+SIZE]);
            to[j] = newvalue;
        }

        //right side
        initialValue = from[startIndex+SIZE-1];
        newvalue = initialValue;
        newvalue += transferAmount(initialValue, from[startIndex+SIZE-1-1]);
        newvalue += transferAmount(initialValue, from[startIndex+SIZE-1+SIZE]);
        to[startIndex+SIZE-1] = newvalue;
        return;
    }
    //check if last line
    if (startIndex == SIZE * (SIZE - 1)) {
        int initialValue = from[startIndex];
        int newvalue = initialValue;
        newvalue += transferAmount(initialValue, from[startIndex+1]);
        newvalue += transferAmount(initialValue, from[startIndex-SIZE]);
        to[startIndex] = newvalue;

        for (int j = startIndex + 1; j < startIndex + SIZE - 1; j++){
            initialValue = from[j];
            newvalue = initialValue;
            newvalue += transferAmount(initialValue, from[j+1]);
            newvalue += transferAmount(initialValue, from[j-1]);
            newvalue += transferAmount(initialValue, from[j-SIZE]);
            to[j] = newvalue;
        }

        //right side
        initialValue = from[startIndex+SIZE-1];
        newvalue = initialValue;
        newvalue += transferAmount(initialValue, from[startIndex+SIZE-1-1]);
        newvalue += transferAmount(initialValue, from[startIndex+SIZE-1-SIZE]);
        to[startIndex+SIZE-1] = newvalue;
        return;
    }

    //seperate the cases for first and last number
    //left side
    int initialValue = from[startIndex];
    int newvalue = initialValue;
    newvalue += transferAmount(initialValue, from[startIndex+1]);
    newvalue += transferAmount(initialValue, from[startIndex+SIZE]);
    newvalue += transferAmount(initialValue, from[startIndex-SIZE]);
    to[startIndex] = newvalue;

    for (int j = startIndex + 1; j < startIndex + SIZE - 1; j++){
        initialValue = from[j];
        newvalue = initialValue;
        newvalue += transferAmount(initialValue, from[j+1]);
        newvalue += transferAmount(initialValue, from[j-1]);
        newvalue += transferAmount(initialValue, from[j+SIZE]);
        newvalue += transferAmount(initialValue, from[j-SIZE]);
        to[j] = newvalue;
    }

    //right side
    initialValue = from[startIndex+SIZE-1];
    newvalue = initialValue;
    newvalue += transferAmount(initialValue, from[startIndex+SIZE-1-1]);
    newvalue += transferAmount(initialValue, from[startIndex+SIZE-1+SIZE]);
    newvalue += transferAmount(initialValue, from[startIndex+SIZE-1-SIZE]);
    to[startIndex+SIZE-1] = newvalue;
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

    alignas(64) int * field1 = calloc(SIZE*SIZE, sizeof(int));
    alignas(64) int * field2 = calloc(SIZE*SIZE, sizeof(int));
    setupField(field1);


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
                .from = field1,
                .to = field2,
                .step = step,
                .startIndex = (j * 2 + o) * SIZE
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