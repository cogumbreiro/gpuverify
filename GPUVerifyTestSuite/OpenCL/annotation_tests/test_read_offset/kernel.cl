//pass
//--local_size=64 --num_groups=64


__kernel void foo()
{
    __local float A[1024];
    __invariant(__implies(__read(A), __read_offset(A) == 0));
}