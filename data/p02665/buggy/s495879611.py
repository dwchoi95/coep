N=int(input())
A=list(map(int,input().split()))
temp=1
summ=0
cont=0
templist=[1]
for i in range(N+1):
  
  if A[i]<temp:
    if i<N:
      summ+=temp
      temp=2*(temp-A[i])
      templist.append(temp)
    elif i==N:
      summ+=temp
      cont+=1
  elif A[i]==temp:
    if i==N:
      summ+=temp
      
      cont+=1
    else:
      print("-1")
      break
  else:
    print("-1")
    break
    
if cont==1:
  if A[N]==temp:
  	print(summ)
  else:
    
    
    comp=A[-1]
    for i in range(N):
      summ-=(templist[-(i+1)]-comp)
      comp+=A[-(i+2)]
      
      
      
      if comp>templist[-(i+2)]:
        print(summ)
        break

