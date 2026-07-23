n = int(input())
mount = [0]*n
a = list(map(int, input().split()))
b = list(map(int, input().split()))
mount[0] = a[0]
mount[-1] = b[-1]
pat = 1
mod = 10**9+7
for i in range(1,n):
  if a[i] > a[i-1]:
    if mount[i] != 0 and mount[i] != a[i]:
      print(0)
      exit()
    else:
      mount[i] = a[i]
  if b[n-i-1] > b[n-i]:
    if mount[n-i-1] != 0 and mount[n-i-1] != b[n-i-1]:
      print(0)
      exit()
    else:
      mount[n-i-1] = b[n-i-1]
for i in range(n):
  if mount[i] == 0:
    dx = 1
    while mount[i+dx] == 0:
      dx += 1
    this = min(mount[i-1],mount[i+dx])
    pat = pat*(this**dx)%mod
    for j in range(dx):
      mount[i+j] = this
a2 = [0]*n
b2 = [0]*n
a2[0] = mount[0]
b2[-1] = mount[-1]
for i in range(1,n):
  a2[i] = max(mount[i],a2[i-1])
  b2[n-i-1] = max(mount[n-i-1],b2[n-i])
if a != a2 or b != b2:
  print(0)
else:
  print(pat)