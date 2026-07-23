n=int(input())
d=map(int,input().split())
d=list(d)
kotae=0
for i in range(n):
  for j in range(n-i-1):
    kotae=kotae+d[i]*d[j]
print(kotae)