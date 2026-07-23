n=int(input())
d=list(map(int,input().split()))

kotae=0
for i in range(n):
  for j in range(i+1,n):
    kotae=kotae+d[i]*d[j]
print(kotae)
