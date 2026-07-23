import statistics
n=int(input())
x=[int(_) for _ in input().split()]
mid=int(statistics.mean(x))
mmid=mid-1
cnt=0
cntm=0
for i in range(len(x)):
  cnt+= (x[i]-mid)**2
  cntm+=(x[i]-mmid)**2
print(min(cnt,cntm))
  