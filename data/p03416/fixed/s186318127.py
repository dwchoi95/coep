a,b=map(int,input().split())
count=0
for i in range(a,b+1):
    i=str(i)
    if i[:3]==i[:1:-1]:
        count+=1
print(count)