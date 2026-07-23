def dfs(index):
    global ans
    if index == N :
        if blst.count(1) >= K - 1:
            tmp = a1
            anstmp = 0
            for i in range(1, N):
                if blst[i - 1] == 0:continue
                if tmp >= a[i]:
                    anstmp += tmp - a[i] + 1
                    tmp += 1
            ans = min(ans, anstmp)
        return
    for i in range(2):
        blst[index - 1] = i
        dfs(index + 1)
    return

N, K = map(int, input().split())
a = list(map(int, input().split()))
blst = [0] * (N - 1)
a1 = a[0]
ans = 10 ** 18
dfs(1)

print(ans)