from collections import defaultdict
row=defaultdict(int)
col=defaultdict(int)
H,W,M=map(int,input().split())

matrix=defaultdict(bool)
for i in range(M):
    h,w=map(int,input().split())
    row[h-1]+=1
    col[w-1]+=1
    matrix[(h-1,w-1)]=True




temp=list(row.items())
temp.sort(key=lambda x:x[1])
a,b=temp[-1][0],temp[-1][1]
cnt=0
for i in range(W):
    temp=0
    if matrix[(a,i)]:
        temp=(b+col[i]-1)
    else:
        temp=(b+col[i])
    cnt=max(cnt,temp)

temp=list(col.items())
temp.sort(key=lambda x:x[1])
a,b=temp[-1][0],temp[-1][1]
cnt2=0
for i in range(H):
    temp=0
    if matrix[(a,i)]:
        temp=(b+row[i]-1)
    else:
        temp=(b+row[i])
    cnt2=max(cnt2,temp)
print(max(cnt,cnt2))