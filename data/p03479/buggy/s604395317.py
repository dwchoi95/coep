import sys
input = sys.stdin.readline

x, y = map(int, input().split())
ans = 0
for k in range(1, 40):
    
    if int(y / (x * 2**k)) < 1:
        ans = k
        break
print(ans)