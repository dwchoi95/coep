N = int(input())
CSF = [list(map(int, input().split())) for i in range(N-1)]
for i in range(N-1):
    ans = 0
    for j in range(i, N-1):
        C, S, F = CSF[j]
        if ans < S:
            ans = S
        else:
            if ans % F != 0:
                ans += F - (ans % F)
        ans += C
    print(ans)
print(0)