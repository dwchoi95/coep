N = int(input())
c = [list(map(int, input().split())) for _ in range(N - 1)]
anslst = [0] * N
for i in range(N - 1):
    ans = c[i][1] + c[i][0]
    for j in range(i + 1, N - 1):
        if ans <= c[j][1]:
            ans = c[j][1] + c[j][0]
        else:
            tmp = ans - c[j][1]
            amari = tmp % c[j][2]
            if amari == 0:
                ans += c[j][0]
            else:
                ans += c[j][0] + amari

    anslst[i] = ans

for i in anslst:
    print(i)