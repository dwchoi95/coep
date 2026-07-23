n,k = map(int,input().split())
s = str(input())
b = s[k-1].lower()
print(s[:k-1]+b+s[k:])