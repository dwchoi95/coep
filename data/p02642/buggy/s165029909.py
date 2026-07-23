from collections import Counter
import bisect
N = int(input())
A = list(map(int,input().split()))



cnt = Counter(A)
A.sort()
ans = 0
for i in range(len(A)):
    if cnt[A[i]] > 1:
        continue
    idx = bisect.bisect_right(A, pow(A[i],0.5))
    J = min(idx+1,i)
    
    ok = True
    for j in range(J):
        
        if A[i] % A[j] == 0:
            ok = False
            break
    if ok:
        ans += 1
print (ans)

