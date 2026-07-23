from itertools import accumulate

n, q = map(int, input().split())
s = list(input())

z = []
for i in range(n-1):
    if s[i] + s[i+1] == 'AC':
        z.append(1)
    else:
        z.append(0)


z = [0] + list(accumulate(z))


for j in range(q):
    l, r =  map(int, input().split())
    print(z[r-1] - z[l-1])
