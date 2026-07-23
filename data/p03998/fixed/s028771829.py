A=input()
B=input()
C=input()
s="a"
while (len(A)!=0 or s!="a") and (len(B)!=0 or s!="b") and (len(C)!=0 or s!="c"):
  if s=="a":
    s=A[0]
    A=A[1:]
  elif s=="b":
    s=B[0]
    B=B[1:]
  else:
    s=C[0]
    C=C[1:]
if len(A)==0 and s=="a":
    print("A")
elif len(B)==0 and s=="b":
    print("B")
else:
    print("C")
