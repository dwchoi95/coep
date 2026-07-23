N,M = map(int,input().split())
li={}
for i in range(N):
	a,b = map(int,input().split())
	li[a]=b
li=sorted(li.items())
m_sum=0
for k,v in li:
	if v<M:
		M-=v
		m_sum+=k*v
	else:
		m_sum+=k*M
		break
print(m_sum)
