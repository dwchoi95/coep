n = int(input())
x = list(map(int,input().split()))
m = 10**10
for p in range(x[0],x[n-1]+1):
    power = 0
    for i in range(n):
        power += (x[i]-p)**2
    m = min(m,power)
print(m)