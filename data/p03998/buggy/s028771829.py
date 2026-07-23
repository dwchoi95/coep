A=input()
B=input()
C=input()
s="a"
while len(A)!=0 and len(B)!=0 and len(C)!=0:
  if s=="a":
    s=A[0]
    A=A[1:]
    continue
  if s=="b":
    s=B[0]
    B=B[1:]
    continue
  if s=="c":
    s=C[0]
    C=C[1:]
    continue
if len(A)==0:
  print("A")
elif len(B)==0:
  print("B")
else:
  print("C")
