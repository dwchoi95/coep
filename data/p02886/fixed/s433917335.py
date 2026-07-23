N = int(input())
A = list(map(int, input().split())) 
X = 0
for a in range(N):
    if a+1 < N:
        x = A[a]
        y = sum(A[(a+1):(N+1)])
        X += x*y

print(X)