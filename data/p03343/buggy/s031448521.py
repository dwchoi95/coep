n,k,q=map(int,input().split())
arr=list(map(int,input().split()))
arr2=sorted(arr)
ans=10**18
m=arr2[0]
for val in arr:
  tmp=[]
  vals=[]
  for i in range(n):
    if arr[i]>=val:
      tmp.append(arr[i])
    else:
      if len(tmp)>=k:
        tmp=sorted(tmp)
        vals.extend(tmp[:len(tmp)-k+1])
        tmp=[]
  if len(tmp)>=k:
    tmp=sorted(tmp)
    vals.extend(tmp[:len(tmp)-k+1])
  if len(vals)<q:
    continue
  else:
    vals=sorted(vals)
    ans=min(ans,vals[q-1]-vals[0])
print(ans)