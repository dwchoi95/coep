n = int(input())
a = [int(i) for i in input().split()]
b = [int(i) for i in input().split()]
count = 0
left = 0
for i in range(n):
    if b[i] + left - a[i] >= 0:
        count += a[i]
        left = b[i] + left - a[i]
        if left > b[i]:
            left = b[i]
    else:
        count += b[i] + left
        left = 0

count += min(left, a[n])
print(count)