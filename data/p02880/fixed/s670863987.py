N = int(input())
printed = False
try:
    for i in range(1, 10):
        for j in range(1, 10):
            if N == i * j:
                print('Yes')
                printed = True
                raise Exception
except Exception:
    pass

if not printed:
    print('No')