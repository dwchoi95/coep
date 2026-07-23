import copy
n,k=map(int,input().split())

s=list(input())

print(s[0:k-1],end='')
print(s[k-1].lower(),end='')
print(s[k:],end='')