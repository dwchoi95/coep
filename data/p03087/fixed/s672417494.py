n, q = map(int, input().split())
s = input()

ac = [0 for i in range(n)]
for i in range(1, n):
    if s[i - 1] == 'A' and s[i] == 'C':
        ac[i] = 1

for i in range(n - 1):
    ac[i + 1] += ac[i]
for i in range(q):
    l, r = map(int, input().split())
    l -= 1
    r -= 1
    ret = ac[r] - ac[l]
    print(ret)
