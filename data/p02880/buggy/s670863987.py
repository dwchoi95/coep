N = input()
printed = False
for i in range(1, 10):
    for j in range(1, 10):
        if N == i * j:
            print('Yes')
            printed = True
            break

if not printed:
    print('No')