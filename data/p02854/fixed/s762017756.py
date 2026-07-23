import sys

n = int(input())

a = list(map(int, input().split()))

cnt = 0
ave = sum(a)/2

for i in range(n):
    cnt += a[i]
    if cnt == ave:
        print(0)
        sys.exit()
    
    elif cnt > ave:
        x = ave -cnt +a[i]
        if x >= cnt -ave:
            x = cnt -ave
        break

print(int(x*2))