N = int(input())
D = list(map(int, input().split()))

sum_all = 0
for i in range(N):
  for s in range(i, N):
    sum_all += D[i] * D[s]
    
print(sum_all)