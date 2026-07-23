def gcd(x,y):
    if x<y:
        x,y = y,x
    while y>0:
        x,y = y,x%y
    return x
N = int(input())
T = list(set([int(input()) for _ in range(N)]))
a = T[0]
for i in range(1,len(T)):
    a = gcd(T[i],a)
t = a
for i in range(len(T)):
    t *= T[i]
print(t)