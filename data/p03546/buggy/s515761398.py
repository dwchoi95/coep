h,w=map(int,input().split())
c=[]
for i in range(10):
	c.append(list(map(int,input().split())))
a=[]
ans=0
for i in range(h):
	a.append(list(map(int,input().split())))
for i in range(10):
	for j in range(10):
		for k in range(10):
			c[i][j]=min(c[i][j],c[i][k]+c[k][j])
for j in range(h):
	for k in range(w):
		if a[j][k]==-1 or a[j][k]==1:
			continue
		else:
			ans+=c[a[j][k]][1]
print(ans)
					