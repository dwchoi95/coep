n,k=list(map(int,input().split()))
s=str(input())

y=s[:k-1]+s[k-1].lower()+s[k:]

print(y)