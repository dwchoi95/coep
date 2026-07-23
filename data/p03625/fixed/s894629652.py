n=int(input())
a=list(map(int,input().split()))
a.sort(reverse=True)

ans=[]
tmp=0
count=0
for el in a:
    if len(ans)==2: break
    if el != tmp: tmp=el; count=0
    else:
        if count%2==0: ans.append(el); tmp=el;
        count+=1

try: ans=ans[0]*ans[1]
except: ans=0
print(ans)
