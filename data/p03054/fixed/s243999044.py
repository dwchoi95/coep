import sys
sys.setrecursionlimit(10 ** 7)
input = sys.stdin.readline

h, w,n = map(int, input().split())
r,c = map(int, input().split())
s = input() 
t = input() 


x=c
for i in range(n):
    if s[i] == 'R' : x+=1
    if x == w+1:
        print('NO')
        exit()
    if t[i] == 'L' and x>1 : x-=1


x=c
for i in range(n):
    if s[i] == 'L' : x-=1
    if x == 0:
        print('NO')
        exit()
    if t[i] == 'R' and x<w: x+=1


y=r
for i in range(n):
    if s[i] == 'U' : y-=1
    if y == 0:
        print('NO')
        exit()
    if t[i] == 'D' and y<h: y+=1


y=r
for i in range(n):
    if s[i] == 'D' : y+=1
    if y == h+1:
        print('NO')
        exit()
    if t[i] == 'U' and y>1: y-=1

print('YES')
