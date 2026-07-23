n = int(input())
a = list(map(int,input().split()))
b = sum(a)
l = 0
r = 0
x = 0
ans = 0
for i in a:
  l += i
  r = b - l
  if l==r:
    break;
  elif l>r:
    ans = min(l-r,y-x)
    print(l-r,y-x)
    break;
  x = l
  y = r
print(ans)