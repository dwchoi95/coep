n=int(input())
a=list(map(int,input().split()))
a.sort(reverse=True)

ans=[]
tmp=0
flag=True
for el in a:
    if len(ans)==2: break
    if el != tmp: tmp=el; flag=True
    else:
        if flag: ans.append(el); tmp=el; flag=False

try: ans=ans[0]*ans[1]
except: ans=0
print(ans)
