import math
s=int(input())
if s==1:
  print("0 0 1 0 0 1")
  exit()
c=math.ceil(math.sqrt(s))
sa=c**2-s
for i in range(1, s):
  if sa%i==0 and sa/i <= 10**9:
    print("0 0 {} {} {} {}".format(c, i, sa
    exit()