import sys
sys.setrecursionlimit(10 ** 7)
input = sys.stdin.readline

h, w,n = map(int, input().split())
r,c = map(int, input().split())
s = input() 
t = input() 

toL = c
toR = w-c+1
toU = r
toD = h-r+1


cntR=0
for i in range(n):
    if s[i] == 'R' : cntR+=1
    if cntR == toR:
        print('NO')
        exit()
    if t[i] == 'L' and cntR>0 : cntR-=1


cntL = 0
for i in range(n):
    if s[i] == 'L' : cntL+=1
    if cntL == toL:
        print('NO')
        exit()
    if t[i] == 'R' and cntL>0: cntL-=1


cntU = 0
for i in range(n):
    if s[i] == 'U' : cntU+=1
    if cntU == toU:
        print('NO')
        exit()
    if t[i] == 'D' and cntU>0: cntU-=1


cntD = 0
for i in range(n):
    if s[i] == 'D' : cntD+=1
    if cntD == toD:
        print('NO')
        exit()
    if t[i] == 'U' and cntD>0: cntD-=1

print('YES')
