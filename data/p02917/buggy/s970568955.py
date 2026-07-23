n=int(input())
b=list(map(int,input().split()))
for j in range(n-2):
    if b[j]>min(b[j:]):
        b[j]=min(b[j:])

print(sum(b)+b[0])