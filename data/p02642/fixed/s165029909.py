from collections import Counter
import bisect
N = int(input())
A = list(map(int,input().split()))



cnt = Counter(A)
A.sort()
ans = 0
P = [0] * (10**6+1)

for a in A:
    if P[a]==0:
        for i in range(10**7):
            x = a*i
            if x>10**6:
                break
            P[x] = 1
        if cnt[a]==1:
            ans +=1

print (ans)


