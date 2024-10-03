#include <stdio.h>
#include <stdlib.h> 
#include <string.h>
#include <time.h>
#include <math.h>
#include <sys/time.h>

int INPUTFIELDSIZE = 7;

struct timeval tval_before, tval_after, tval_result;


int SIZE = 0, 
    ITERATIONS = 0,
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

void updateLoop(int ** f,int ** f2) {
    for (int i = 0; i < SIZE; i++){
        for (int j = 0; j < SIZE; j++){
            int v = f[i][j];
            f2[i][j] = v;
            if (i < SIZE - 1)
            {
                f2[i][j] += transferAmount(v, f[i+1][j]);
            }
            if (i > 0)
            {
                f2[i][j] += transferAmount(v, f[i-1][j]);
            }
            if (j < SIZE - 1)
            {
                f2[i][j] += transferAmount(v, f[i][j+1]);
            }
            if (j > 0)
            {
                f2[i][j] += transferAmount(v, f[i][j-1]);
            }
        }
    }
}
    

void setupField(int ** f) {
    int center = (SIZE - INPUTFIELDSIZE) / 2;
    int res = pow((double)SIZE,(double)3);
    for (size_t i = 0; i < res  ; i++)
    {
        f[rand() % SIZE][rand() % SIZE] += (rand() % 50);
    }
}


int main(int argc, char const *argv[]) {
    SEED = time(0);
    for (int i = 1; i < argc; i += 2) {
        if (!strcmp(argv[i], "-s")) {
            SIZE = atoi(argv[i + 1]);
        } else if (!strcmp(argv[i], "-i")) {
            ITERATIONS = atoi(argv[i + 1]);
        } else if (!strcmp(argv[i], "-seed")) {
            SEED = atoi(argv[i + 1]);
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
    for (int  i = 0; i < SIZE; i++)
    {
        fieldinput[i] = (int*) calloc(SIZE, sizeof(int));
    }
    field1[2][2] = 100;

    gettimeofday(&tval_before, NULL);

    for (size_t i = 0; i < ITERATIONS/2; i++)
    {
        updateLoop(field1,field2);
        updateLoop(field2,field1);
    }
    gettimeofday(&tval_after, NULL);
    timersub(&tval_after, &tval_before, &tval_result);
    unsigned long time_in_micros = 1000000 * tval_result.tv_sec + tval_result.tv_usec;
    printMatrice(field1);
    return 0;
}