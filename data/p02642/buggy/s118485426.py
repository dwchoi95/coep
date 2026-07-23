from collections import defaultdict

N = int(input())
A = list(map(int, input().split()))
A.sort()
dic = defaultdict(int)
for a in A:
    dic[a] += 1
ans = 0
for a in A:
    if dic[a] > 1: continue
    else:
        ans += 1
        idx = 1
        while a*idx <= 10**6:
            dic[a*idx] += 1
            idx += 1
print(ans)
