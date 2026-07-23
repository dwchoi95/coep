from collections import Counter
N = int(input())
A_list = list(map(int, input().split()))
counter = Counter(A_list)
counter = sorted(counter.items(), key=lambda x: -x[0])

long_side = 0
short_side = 0
choice = 0

for k, v in counter:
    if v >= 4 and choice == 0:
        long_side = k
        short_side = k
        choice = 4

    elif v >= 2:
        if choice == 2:
            short_side = k
            choice = 4
        else:
            long_side = k
            choice = 2

    if choice == 4:
        print(long_side*short_side)
        exit()
print(0)