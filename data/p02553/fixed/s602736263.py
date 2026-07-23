a, b, c, d = input().split()

a=int(a)
b=int(b)
c=int(c)
d=int(d)

X1 = min(a,b) * min(c,d)
X2 = min(a,b) * max(c,d)
X3 = max(a,b) * min(c,d)
X4 = max(a,b) * max(c,d)

print(max(X1,X2,X3,X4))
