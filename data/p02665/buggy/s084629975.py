
N = int(input())

A = list(map(int, input().split()))
for i in range(N):
    if A[i] > 2**i:
        print(-1)
        exit()

if A[0] != 0:
    if N == 0 and A[0] == 1:
        print(1)
        exit()
    else:
        print(-1)
        exit()

limit = [1]
for i in range(1, N+1):
    if i == N:
        limit.append(A[i])
    else:
        limit.append((limit[-1]-A[i-1])*2)



ans = [A[-1]]
now_leaf = A[-1]
for i in range(N-1, -1, -1):
    
    ans.append(min(now_leaf+A[i], limit[i]))
    now_leaf = ans[-1]

print(sum(ans))
