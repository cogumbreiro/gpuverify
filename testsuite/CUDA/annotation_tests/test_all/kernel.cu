//pass
//--blockDim=64 --gridDim=64 --no-inline

#include <cuda.h>

__global__ void foo(int* A)
{

  __assert(__all(threadIdx.x < blockDim.x));

}
