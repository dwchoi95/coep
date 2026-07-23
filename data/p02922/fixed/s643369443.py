A, B = map(int, input().split())
sum = 0
i = 1
if B != 1:
    while sum < B:
        sum = A + (A-1)*(i-1)
        i += 1
    print(i-1)
else:
    print(0)