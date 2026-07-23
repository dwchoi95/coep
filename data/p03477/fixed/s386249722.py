A,B,C,D = map(int,input().split())

l=A+B
r=C+D

if r>l:
    print("Right")
elif l>r:
    print("Left")
else:
    print("Balanced")