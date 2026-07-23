a = list(map(int,input().split()))

k = a[1]
i = 2
l = a[0]
while True:
  l *= 2
  if k < l:
    break
  i += 1
print(i-1)
