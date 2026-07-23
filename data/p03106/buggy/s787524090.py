A,B,K=(int(x) for x in input().split())

val = 1
lcnt = 0
while True:
  if A % val == 0 and B % val == 0:
    lcnt += 1
  if lcnt == K:
    break
  val += 1
print(val)