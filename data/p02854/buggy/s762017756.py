import sys

n = int(input())

a = list(map(int, input().split()))

cnt = 0
sum_ = sum(a)/2

for i in range(n):
    cnt += a[i]
    if cnt == sum_:
        print(0)
        sys.exit()
    elif cnt > sum_:
        x1 = sum_ -cnt +a[i-1]
        if x1 <= cnt -sum_:
            x1 = cnt -sum_
        break

print(int(x1*2))