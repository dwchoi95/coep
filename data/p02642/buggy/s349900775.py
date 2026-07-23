from collections import deque

N = int(input())
A = list(map(int,input().split()))

A.sort()

ans = 0
max_A = max(A)
ban = [0]*(max_A+1)
again = list()

last = 0
for i in range(N-1):
    if A[i] == A[i+1] and A[i] != last:
        again.append(A[i])
        last = A[i]
if A[N-1] != A[N-2]:
    again.append(A[N-1])

for num in again:
    ban_num = num
    while ban_num <= max_A:
        ban[ban_num] = 1
        ban_num += num
 
for num in A:
    if ban[num] != 1:
        ans += 1
        ban_num = num
        while ban_num <= max_A:
            ban[ban_num] = 1
            ban_num += num

print(ans)