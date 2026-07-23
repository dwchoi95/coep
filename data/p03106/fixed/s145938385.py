a,b,k=map(int,input().split())
numlst=[]
for i in range(max(a,b)):
    if a%(i+1)==0 and b%(i+1)==0:
        numlst.append(i+1)

print(numlst[len(numlst)-k])