from collections import Counter
n=int(input())
a=list(map(int,input().split()))
x1=0
x2=0
count=Counter(a)
for i in count:
  if count[i]>=4:
    if x1<=i:
      x2=i
      x1=i
  if count[i]>=2:
    if x1<=i:
      x2=x1
      x1=i
    elif x2 <= i < x1:
      x2=i
print(x1*x2)