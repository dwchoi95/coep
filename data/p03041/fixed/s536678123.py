n,k=map(int,input().split())

s=str(input())

print(s[0:k-1],end='')
print(s[k-1].lower(),end='')
print(s[k:],end='')