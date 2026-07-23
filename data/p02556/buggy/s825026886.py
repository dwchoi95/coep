n=int(input())
arr=[]
s=set()
for _ in range(n):
	x,y=map(int,input().split())
	if((x,y) not in s):
		arr.append(x+y)
		s.add((x,y))
arr.sort()
if(len(arr)==1):
	print(0)
else:
	print(arr[-1]-arr[0])