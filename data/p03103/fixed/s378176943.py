N, M = map(int, input().split())
AB = []
for i in range(N):
    a, b = map(int, input().split())
    AB.append([a,b])

sortedAB = sorted(AB, key=lambda x:x[0])

ans = 0
for i in range(N):
    a = sortedAB[i][0]
    b = sortedAB[i][1]
    if M == 0:
        print(ans)
        exit()
    if b <= M:
        ans += a*b
        M -= b
    else:
        ans += a*M
        M = 0

print(ans)      