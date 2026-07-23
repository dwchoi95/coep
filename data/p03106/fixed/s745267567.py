a, b, k = map(int, input().split())
da = []
db = []
dc = []
for i in range(1,a+1):
    if a%i == 0:
    	da.append(i)

for j in range(1, b+1):
    if b%j == 0:
    	db.append(j)

for l in da:
    if l in db:
    	dc.append(l)

dc.sort(reverse = True)
print(dc[k-1])
