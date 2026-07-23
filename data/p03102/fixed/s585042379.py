n,m,c=map(int,input().split())
b=list(map(int,input().split()))
l=[]
ans=[]
cnt=0
for i in range(n):
	a=list(map(int,input().split()))
	l.append(a)
for i in range(n):
	sum=0
	for j in range(m):
		sum+=b[j]*l[i][j]
		if j==(m-1):
			sum+=c
			ans.append(sum)
for i in ans:
	if i>0:
		cnt+=1
print(cnt)
