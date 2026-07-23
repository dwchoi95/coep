N = int(input())
A = list(map(int,input().split()))

even_num = 0

for i in range(N):
    if A[i]%2:
        even_num += 1

print(1*3**(N-1)*even_num+2*3**(N-1)*(N-even_num)-2**(N-even_num))