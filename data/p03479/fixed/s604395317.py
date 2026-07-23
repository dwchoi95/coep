import sys
input = sys.stdin.readline

x, y = map(int, input().split())
ans = 0
while True:
    ans += 1
    temp = x * 2 ** ans
    if temp > y:
        break
print(ans)