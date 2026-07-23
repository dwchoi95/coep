a, b = map(int, input().split())

if b <= 1:
    print(0)
    exit()

x = a

for i in range(1, 100000):
    if x >= b:
        print(i)
        exit()
    x = x + a - 1
