o = list(str(input()))
e = list(str(input()))

for i,j in enumerate(e):
    o.insert(1+2*i,j)
print(o)