n=int(input())
d=list(map(int,input().split(" ")))
wa=[]
for i in range(0,n):
  for j in range(i+1,n):
    wa.append(d[i]*d[j])

print(sum(wa))