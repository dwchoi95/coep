N = int(input())
S = input()

a = 0
for s in S:
  if s=="B":
  	  a += 1
if a > N-a:
	print("Yes")
else:
  	print("No")