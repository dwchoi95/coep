N = int(input())
A = list(map(int,input().split()))

even_num = 0

for i in range(N):
    if A[i]%2==0:
        even_num += 1
print(3**N-2**even_num)