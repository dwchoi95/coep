n=int(input())
d=map(int,input().split(" "))
wa=[]
for i in range(1,n+1):
  for j in range(i,n+1):
    wa.append(i*j)
print(sum(wa))
