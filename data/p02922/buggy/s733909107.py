a, b = map(int, input().split())

if a >= b:
    print(1)
    exit()
    
x = 2 * a - 1

for i in range(2, a + 1):
    if x >= b:
        print(i)
        exit()
    x = x + a - 1
