N = int(input())
table = [[int(i) for i in input().split()] for N in range(N)]

a = -1
b = 10**10
c = -10**10
d = 10**10
for i in range(N):
    p = table[i][0]
    q = table[i][1]
    if a < p+q:
        a = p+q
    if b > p+q:
        b = p+q
    if c < p-q:
        c = p-q
    if d > p-q:
        d = p-q

print(max(a-b,c-d))
