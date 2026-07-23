import sys
input = sys.stdin.readline

n=(int(x) for x in input().split())
l=[x*y for x in range(1,10) for y in range(1,10)]
if n not in l:
    print("No")
else :
    print("Yes")