import sys
input=sys.stdin.readline

s=int(input())




if s<=10**9:
    print(0,0,1,0,0,s)
    exit()

y=s
x=s%(10**9)

print(0,0,10**9,1,x,y)


