N = int(input())
A = list(map(int, input().split()))

if N == 0:
    if A[0] != 1:
        print(-1)
    else:
        print(1)
    exit()


leaf = []
miki = []
under = 1

for i, a in enumerate(A):
    if a > under:
        print(-1)
        exit()
    miki.append(under - a)
    under = miki[-1] * 2


ans = 0
child = 0
for i in reversed(range(N + 1)):
    child = min(child, miki[i]) + A[i]
    ans += child

print(ans)