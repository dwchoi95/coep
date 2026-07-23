A, B, K = map(int,input().split())

count = 0

for i in range(1, min(A, B) + 1, 1):
  if A % i and B % i:
    count += 1
    
  if count == K:
    print(i)