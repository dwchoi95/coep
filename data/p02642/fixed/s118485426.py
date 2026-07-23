from collections import defaultdict

N = int(input())
A = list(map(int, input().split()))
A.sort()
dic = defaultdict(int)
for a in A:
    dic[a] += 1
ctr = defaultdict(int)
ans = 0
for a in A:
    if dic[a] == 1 and ctr[a] == 0:
        ans += 1
    if ctr[a] == 0:
        m = 1
        while a*m <= 10**6:
            ctr[a*m] += 1
            m += 1
print(ans)
