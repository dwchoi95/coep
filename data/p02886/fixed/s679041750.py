N = int(input())
D = list(map(int, input().split()))

ret = 0

for i in range(N):
    for j in range(i+1, N):
        if i == j:
            continue

        ret += D[i] * D[j]

print(ret)