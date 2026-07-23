import random
N = int(input())
a = [int(ai) for ai in input().split()]

count = 0
for i in range(0, N-1):
    if a[i] == a[i+1]:
        count += 1
    while a[i] == a[i+1]:
        a[i+1] = random.randint(1, N)
print(count)