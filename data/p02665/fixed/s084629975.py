
N = int(input())

A = list(map(int, input().split()))


limit = [1]
for i in range(1, N+1):
    if i == N:  
        limit.append(A[i])
    else:
        limit.append((limit[-1]-A[i-1])*2)
        if limit[-1] < 0:
            print(-1)
            exit()


if N == 0:
    if A[0] != 1:
        print(-1)
        exit()


ans = [A[-1]]
now_leaf = A[-1]  
for i in range(N-1, -1, -1):
    
    ans.append(min(now_leaf+A[i], limit[i]))
    now_leaf = ans[-1]

for i in range(N):
    
    if (ans[N-i]-A[i])*2 < A[i+1]:  
        print(-1)
        exit()
print(sum(ans))
