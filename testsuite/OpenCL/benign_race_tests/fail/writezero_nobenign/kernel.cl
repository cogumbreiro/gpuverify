//xfail:BOOGIE_ERROR
//--local_size=64 --num_groups=1 --no-benign --no-inline
//kernel.cl: error: possible write-write race on


__kernel void foo(__local int* A, __local int* B, int i, int j) {
  A[0] = 0;
}
