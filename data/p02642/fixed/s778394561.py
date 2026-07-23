from collections import Counter
import bisect
n = int(input()) 
a = list(map(int, input().split())) 
cnt = Counter(a) 
a.sort()
ans = 0
mx = 10 ** 6
p = [0] * (mx + 1)
for i in a:
    if p[i] == 0:
        for j in range(mx + 1):
            x = i * j
            if x > mx:
                break
            p[x] = 1 
        if cnt[i] == 1:
            ans += 1 
print(ans)