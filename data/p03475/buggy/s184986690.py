N = int(input())
L = [list(map(int, input().split())) for i in range(N-1)]
ans = []

for i in range(N-1):
    time = L[i][1]
    for j in range(i, N-1):
        c, s, f = L[j]
        if time >= s:
            time += f - (time % f) 
        else:
            time += s - time
        time += c
    ans.append(time)

ans.append(0)
print(*ans, sep="\n")