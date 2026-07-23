n = int(input())
x = list(map(int,input().split()))
m = 0
j = max(x)

for p in range(j):
    c = 0
    for i in range(n):
        p = (i+1) * (i+1) - n
        c = c + (p * p)
    
    if m == 0:
        m = c
    else:
        if m > c:
            m = c

print(c)