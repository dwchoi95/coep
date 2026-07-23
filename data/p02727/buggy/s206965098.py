from heapq import heappush, heappop

x, y, a, b, c = map(int, input().split())
p = list(map(int, input().split()))
q = list(map(int, input().split()))
r = list(map(int, input().split()))

hp = []
for e in p:
    heappush(hp, [-e, 0])
for e in q:
    heappush(hp, [-e, 1])
for e in r:
    heappush(hp, [-e, 2])

ans = 0
cnt = [0] * 3
sm = 0
mx = [c, x, y]
while hp:
    yum, col = heappop(hp)
    yum = -yum

    if cnt[col] >= mx[col]:
        continue

    ans += yum
    cnt[col] += 1
    sm += 1

    if sm == x + y:
        break

print(ans)
