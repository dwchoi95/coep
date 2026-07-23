A, B = map(int, input().split())

count = 0
for q in range(A, B + 1):
    w = str(q)
    if w[:2] == (w[-1] + w[-2]):
        count += 1
print(count)
