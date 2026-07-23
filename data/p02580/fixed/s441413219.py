from collections import defaultdict
n,m,k=map(int,input().split())
points=set()
row=defaultdict(int)
col=defaultdict(int)
for i in range(k):
    a,b=map(int,input().split())
    points.add((a,b))
    row[a]+=1
    col[b]+=1
m1=max(row.values())
m2=max(col.values())
l1=[]
l2=[]
for i in row:
    if row[i]==m1:
        l1.append(i)
for i in col:
    if col[i]==m2:
        l2.append(i)
ans=m2+m1-1
for i in l1:
    for j in l2:
        if (i,j) not in points:
           
            ans+=1
            print(ans)
            quit()
print(ans)


