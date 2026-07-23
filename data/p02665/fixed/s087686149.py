N = int(input())

A = list(map(int,input().split()))
s = sum(A[1:])
B = [0] * (N+1)
B[0] = 1 - A[0]
for i in range(0,N):
    s -= A[i+1]
    if 2*B[i] < A[i+1]:
        print("-1")
        exit()
    B[i+1] = min(2*B[i]-A[i+1],s)
if B[-1] != 0:
    print("-1")
else:
    print(sum(A)+sum(B))
