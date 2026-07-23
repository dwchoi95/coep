n = int(input())
b = list(map(int, input().split()))

a = [0]*n
a[0] = b[0]
a[-1] = b[-1]
for i in range(n-2):
    if b[i] > b[i+1]:
        b[i] = b[i+1]
    a[i+1] = b[i]

print(sum(a))