n = int(input())
x = list(map(int,input().split()))
j = max(x)
m = 0
y = True

for i in range(n):
    if x[0] != x[i]:
        y = False

if y:
    print(0)
    exit(0)

for p in range(j):
    c = 0
    z = 0
    for i in range(n):
        z = x[i] - p
        c = c + (z * z)
    
    if m == 0:
        m = c
    else:
        if m > c:
            m = c

print(m)