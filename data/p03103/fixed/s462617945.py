N, M = map(int, input().split())

shop_list = [None] * N
for n in range(N):
    a, b = map(int, input().split())
    shop_list[n] = [a, b]

total = 0
for a, b in sorted(shop_list, key = lambda x: x[0]):
    if M > b:
        total += a * b
        M -= b
    else:
        total += a * M
        break
print(total)
