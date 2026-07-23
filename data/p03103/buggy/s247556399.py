N,M=map(int,input().split())


AB=[]
for i in range(N):
  ab=list(map(int,input().split()))
  AB.append(ab)


list.sort(AB,key=lambda x:x[0])


m=0 
cost=0 
for i in range(N):
 
 if M-m==AB[i][1]:
     m+=AB[i][1]
     cost+=AB[i][0]*AB[i][1]
     break

 elif M-m<AB[i][1] :
      for j in range(AB[i][1]+1):
         cost=cost+AB[i][0]*j
         m=m+j
         if m==M:
             break
         else:
             cost=cost-AB[i][0]*j
 else:
      cost+=AB[i][0]*AB[i][1]
      m+=AB[i][1]
    
print(cost)