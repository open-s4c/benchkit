#include <stdio.h>
#include <stdlib.h> 
#include <string.h>
#include <time.h>

int INPUTFIELDSIZE = 7;


int SIZE = 0, 
    ITERATIONS = 0,
    SEED;

float CHANGERATE = 0.1;


//https://stackoverflow.com/questions/14166350/how-to-display-a-matrix-in-c
void printMatrice(float** f) {
    int x = 0;
    int y = 0;

    for(x = 0 ; x < SIZE ; x++) {
        printf(" (");
        for(y = 0 ; y < SIZE ; y++){
            printf("%f|", f[x][y]);
        }
        printf(")\n");
    }
}

float somMatrice(float** f) {
    int x = 0;
    int y = 0;
    float r = 0;

    for(x = 0 ; x < SIZE ; x++) {
        printf(" (");
        for(y = 0 ; y < SIZE ; y++){
            r += f[x][y];
        }
        printf(")\n");
    }
    return r;
}

float  transferAmount(int a, int b) {
    return (b - a) *  CHANGERATE;
}

void updateLoop(float ** f,float ** f2) {
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
    

void setupField(float ** f) {
    int center = (SIZE) / 2;
    for (size_t i = 0; i < 500; i++)
    {
        f[center][center] += (rand () % 50);
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

    float ** field1 = calloc(SIZE, sizeof(size_t));
    for (int i = 0; i < SIZE; i++)
    {
        field1[i] = (float *) calloc(SIZE, sizeof(float));
    }
    float ** field2 = calloc(SIZE, sizeof(size_t));
    for (int i = 0; i < SIZE; i++)
    {
        field2[i] = (float *) calloc(SIZE, sizeof(float));
    }
    float ** fieldinput = calloc(SIZE, sizeof(size_t));
    for (int  i = 0; i < SIZE; i++)
    {
        fieldinput[i] = (float*) calloc(SIZE, sizeof(float));
    }
    //setupField(field1);
    field1[2][2] = 100;
    
    for (size_t i = 0; i < ITERATIONS/2; i++)
    {
        updateLoop(field1,field2);
        updateLoop(field2,field1);
    } 
    printMatrice(field1);
    printf("som: %f", somMatrice(field1));
    return 0;
}
