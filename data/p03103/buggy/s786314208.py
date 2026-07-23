import sys
read = sys.stdin.readline


def readln():
    return list(map(int, read().split()))


N, M = readln()

data = {}
for _ in range(N):
    a, b = readln()
    data[a] = b

ans = 0
drink = 0
for k, v in sorted(data.items()):
    ans += k * v
    drink += v
    if drink > M:
        break
print(ans-k*(drink-M))
