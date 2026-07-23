N, M = map(int, input().split())

shop_dic = {}
for _ in range(N):
    a, b = map(int, input().split())
    shop_dic[a] = b

total = 0
for a in sorted(shop_dic.keys()):
    b = shop_dic[a]
    if M < b:
        total += a * M
        break
    else:
        total += a * b
        M -= b
print(total)
