N, M = map(int, input().split())
A = list(map(int, input().split()))
 
sum_A =0
for i in range(N):
    sum_A += A[i]

ans = 0
for i in range(N):
    if (4*M*A[i] >= sum_A):
        ans+=1
    else:
    	ans+=0
    	
if (ans >= M):
    print('Yes')
else:
    print('No')
