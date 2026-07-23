n=int(input())
l= list(map(int, input().split()))
r= list(map(int, input().split()))
l=[0]+l
r.append(0)
 
res=1
if(l[-1]!=r[0]):
	res=0
for i in range(n):
	if( (l[i]<l[i+1]) or (r[i]>r[i+1]) ):
		if( ( (l[i]<l[i+1]) and (r[i]>r[i+1]) ) and (l[i+1]!=r[i]) ):
			res=0
		if( ( (l[i]<l[i+1]) and (r[i]==r[i+1]) ) and (l[i+1]>r[i]) ):
			res=0
		if( ( (l[i]==l[i+1]) and (r[i]>r[i+1]) ) and (l[i+1]<r[i]) ):
			res=0
	else:
		res*=min(l[i],r[i])
		res%=1000000007
print(res)