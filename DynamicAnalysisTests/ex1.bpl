
function BV32_GT (bv32, bv32) : bool;

procedure bar(x: int, y: int)
{
  var $$arr : [bv32]int;
  var a : int;
  var b : int;
  var c : int;
  var d : int;

  b := 4; 
  a, b := b, 0;

  $$arr[0bv32] := 12; 
  while (a < 10)
  {
     c := b + 100 - 5;
     a := a + 1;
     if (a == 0 || a == 9)
     {
        d := $$arr[0bv32];
     }
     else
     {
        $$arr[1bv32] := 15; 
        c := x + $$arr[1bv32];
     }
  }
}

procedure foo (x: bv32, y: bv32)
{
  var a : bv32;
  var b : bv32;

  if (BV32_GT(x, y))
  {
    a := x;
    b := y;
  }
  else
  {
    a := 0bv32;
    b := 1bv32;
  }
}

