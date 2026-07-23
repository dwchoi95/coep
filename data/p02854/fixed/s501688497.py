n = int(input())
a = list(map(int, input().split()))


sum = 0
for i in range(n):
    sum += a[i]

sum2 = 0
for i in range(n):
    sum2 += a[i]
    x = sum2*2 - sum
    if x >= 0:
        y = sum - (sum2-a[i])*2
        if x <= y:
            print(x)
            break
        else:
            print(y)
            break
