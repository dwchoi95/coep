n = int(input())
a = [int(i) for i in input().split()]
print(a)

cnt = 0
for i in range(n):
    if a[i] % 2 == 0:
        cnt += 1

x = 3 ** n - 2 ** cnt

print(x)