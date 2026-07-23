N = int(input())
A = list(map(int, input().split())) 
X = 0
for a in range(1,N+1):
    if a < N:
        X += A[a]*(sum(A[(a+1):(N+1)]))
print(X)