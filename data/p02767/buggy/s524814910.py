n = int(input())
x = list(map(int, input().split()))

max_x = max(x)
min_x = min(x)

ans = []
for i in range(1, 101):
  a = 0
  for xi in x:
    a += (xi - (i+1))*(xi - (i+1))
  ans.append(a)
  
print(min(ans))