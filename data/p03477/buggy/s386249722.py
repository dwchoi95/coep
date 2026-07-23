A,B,C,D = map(int,input().split())

r=A+B
l=C+D

if r>l:
    print("Right")
elif l>r:
    print("Left")
else:
    print("Balanced")