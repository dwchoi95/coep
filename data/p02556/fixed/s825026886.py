n=int(input())
arr=[]
arr2=[]
s=set()
for _ in range(n):
	x,y=map(int,input().split())
	if((x,y) not in s):
		arr.append(x+y)
		arr2.append(x-y)
		s.add((x,y))
arr.sort()
arr2.sort()
if(len(arr)==1):
	print(0)
else:
	ans=arr[-1]-arr[0]
	ans=max(ans,arr2[-1]-arr2[0])
	print(ans)