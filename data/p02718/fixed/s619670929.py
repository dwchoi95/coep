n, m = map(int, input().split())
a = list(map(int, input().split()))

total = sum(a)

count = 0

valid = total / (4 * m)

for i in a:
    if i >= valid:
        count += 1

if count >= m:
    print('Yes')
else:
    print('No')
