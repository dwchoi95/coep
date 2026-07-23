N = int(input())
A = list(map(int, input().split()))
s = [0] * (N + 2)
for i in range(N + 1):
    s[i + 1] = s[i] + A[i]
node, leaf = 1, 1
for d in range(1, N + 1):
    if leaf < A[d]:
        print(-1)
        break
    leaf = min((leaf - A[d - 1]) * 2, s[N + 1] - s[d])
    if leaf < A[d]:
        print(-1)
        break
    node += leaf
else:
    print(node)