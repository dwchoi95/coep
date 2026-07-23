import math
s=int(input())
c=math.ceil(math.sqrt(s))
sa=c*c-s
for i in range(2, s):
  if sa%i==0:
    print("0 0 {} {} {} {}".format(c, i, sa/i, c))
    exit()
    