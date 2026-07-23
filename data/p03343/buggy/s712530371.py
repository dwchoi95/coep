n,k,q=list(map(int,input().split()))
a=list(map(int,input().split()))
sorta=sorted(a)
ans=10**9
for i in sorta:
    A=[]
    l=[]
    flg=1
    for j in a:
      if i>j:
        flg*=-1
      if flg==1:
        l.append(j)
      if flg==-1:
        flg=1
        if len(l)<k:
          l=[]
          continue
        else:
          l.sort()
          A=A+l[:len(l)-k+1]
    if l:
      l.sort()
      A=A+l[:len(l)-k+1]
    if len(A)<q:
      continue
    else:
      A.sort()
      ans=min(ans,A[q-1]-A[0])
print(ans)