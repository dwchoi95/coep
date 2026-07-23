def dfs(index):
    global ans
    if index == N:
        if blst.count(1) >= K - 1:
            tmp = a[0]
            anstmp = 0
            for i in range(1, N):
                if blst[i - 1] == 0:
                    if tmp < a[i]:
                        tmp = a[i]
                    continue
                if tmp >= a[i]:
                    anstmp += tmp - a[i] + 1
                    tmp += 1
                else:
                    tmp = a[i]
            ans = min(ans, anstmp)
        return
    for i in range(2):
        blst[index - 1] = i
        dfs(index + 1)
    return

N, K = map(int, input().split())
a = list(map(int, input().split()))
blst = [0] * (N - 1)
ans = float('inf')
dfs(1)

print(ans)
