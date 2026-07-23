N,M = map(int,input().split())
li = [list(map(int,input().split())) for i in range(N)]
li=sorted(li,key=lambda x: x[0])
m_sum=0
for i in li:
	buy=min(M,i[1])
	m_sum+=i[0]*buy
	M-=buy
print(m_sum)