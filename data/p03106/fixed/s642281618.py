A, B, K = [int(i) for i in input().split()]
tmp = []
for j in range(1, 101):
    if A % j == 0 and B % j == 0:
        tmp.append(j)
tmp = tmp[::-1]
print(tmp[K - 1])