def gcd(x,y):
    if x<y:
        x,y = y,x
    while y>0:
        x,y = y,x%y
    return x
N = int(input())
T = list(set([int(input()) for _ in range(N)]))
t = 1
b = T[0]
for i in range(1,len(T)):
    a = gcd(T[i],b)
    b = a*(T[i]
print(b)