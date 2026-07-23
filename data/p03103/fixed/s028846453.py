N, M = map(int, input().split(" "))
stores = []

for i in range(N):
    Ai, Bi = map(int, input().split(" "))
    stores.append((Ai, Bi))    

price = 0
for a, b in sorted(stores, key=lambda x: x[0]):
    if M <= b:
        price += a * M
        break
    else:
        price += a * b
        M -= b
print(price)
