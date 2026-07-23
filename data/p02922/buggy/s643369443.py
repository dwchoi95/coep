A, B = map(int, input().split())
sum = 0
i = 1
if B != 1:
    sum = A
    while sum < B:
        sum += (A-1)*i
        i += 1
    print(i)
else:
    print(0)