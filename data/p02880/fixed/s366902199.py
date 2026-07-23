import sys
input = sys.stdin.readline

n=int(input())
l=[x*y for x in range(1,10) for y in range(1,10)]
if n in l:
    print("Yes")
else :
    print("No")