N = int(input())

XY_max = -10**10
XY_min = 10**10
YX_max = -10**10
YX_min = 10**10

for _ in range(N):
  x,y = map(int, input().split())
  XY_max = max(XY_max,x+y)
  XY_min = min(XY_min,x+y)
  YX_max = max(YX_max,x-y)
  YX_min = min(YX_min,x-y)

print(max(XY_max-XY_min,YX_max-YX_min))