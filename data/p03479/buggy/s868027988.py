a = list(map(int,input().split()))

k = a[1]
i = 1
l = a[0]
while True:
  l *= i
  if k < l:
    break
  i += 1
print(i-1)
