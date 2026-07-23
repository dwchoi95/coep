N = int(input())
A_leaf = list(map(int, input().split()))
s = [0]*(N+2)
for i in range(1, N+2):
    s[i] = s[i-1] + A_leaf[i-1]
node = [1]*(N+1)
for i in range(1, N+1):
    node[i] = min(node[i-1] - A_leaf[i-1], (s[N+1]-s[i]) / 2)*2
    if node[i] <= 0:
        print(-1)
        break
else:
    print(int(sum(node)))