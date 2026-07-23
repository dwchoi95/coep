l = []
l= list(map(int,input().split()))
ls = sorted(l)
a = ls[0]
b = ls[1]
c = ls[2]

if a + b < c:
	print("Yes")
else:
  	print("No")