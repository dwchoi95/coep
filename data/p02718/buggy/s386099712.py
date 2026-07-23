N, M = map(int, input().split())
A = list(map(int, input().split()))
 
sum_A =0
for i in range(N):
    sum_A += A[i]
 
ans = 1
for i in range(N):
    if (4*M*A[i] < sum_A):
        ans= ans*1
    else:
    	ans =ans*0
 
if (ans != 0):
    print('Yes')
else:
    print('No')