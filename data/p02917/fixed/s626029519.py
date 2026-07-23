n = int(input())
b = list(map(int, input().split()))

a = [0]*n
for i in range(n-1):
    if i == 0:
        a[0] = b[0]
        a[1] = b[0]
    elif b[i] >= b[i-1]:
        a[i+1] = b[i]
    elif b[i] < b[i-1]:
        a[i+1] = b[i]
        a[i] = b[i]
print(sum(a))