import sys
N = int(input())
A = list(map(int, input().split()))

l = []

if A[0] != 0:
    print(-1)
    sys.exit()

for i in range(N):
    if A[i] > A[i+1]+1:
        print(-1)
        sys.exit()

temp = 1
for i in range(N+1):
    l.append(temp-A[i])
    temp = (temp-A[i])*2

ans = 1
node = 0
for i in range(N, 0, -1):
    if l[i-1] >= node + A[i]:
        node += A[i]
        ans += node
    else:
        ans += node + A[i]
        node = l[i-1]

print(ans)