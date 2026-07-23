n=int(input())
a=list(map(str,input().split()))
s=list(reversed(a[1::2]))+a[::2]
c=""
for i in range(n):
    c+=s[i]+" "
print(c)