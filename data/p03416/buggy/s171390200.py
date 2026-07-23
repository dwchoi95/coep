A, B = map(int, input().split())

count = 0
for q in range(A, B):
    if str(q)[:2] == str(q)[-2:]:
        count += 1
print(count)
