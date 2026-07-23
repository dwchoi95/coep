N = int(input())
mant = [0 for _ in range(N)]
for i in range(N):
    x, y = map(int, input().split())
    mant[i] = x + y

print(max(mant)-min(mant))