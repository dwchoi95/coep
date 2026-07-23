n = int(input())
a = [int(i) for i in input().split()]
b = [int(i) for i in input().split()]

count = 0
left = 0
for i in range(n-1,-1, -1):
    if b[i] - a[i+1] + left > 0:
        count += a[i+1]
        left = b[i] - a[i+1] + left
        if left > b[i]:
            left = b[i]
    else:
        count += b[i]
        left = 0

count += min(left, a[0])
print(count)