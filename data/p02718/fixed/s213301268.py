N,M = map(int,input().split())
arr = list(map(int,input().split()))

res = 0
for i in range(N):
    if arr[i] < (1/(4*M)*sum(arr)):
        res = res
    else:
        res += 1

if res >= M:
    print('Yes')
else:
    print('No')