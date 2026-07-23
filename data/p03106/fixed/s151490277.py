A, B, K = map(int,input().split())

count = []

for i in range(1, min(A, B) + 1, 1):
  if (A % i == 0) and (B % i == 0):
    count.append(i)

count.sort(reverse = True)
print(count[K - 1])