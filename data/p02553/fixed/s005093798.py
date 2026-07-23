a,b,c,d=list(map(int, input().split())) 
prod=[]

prod.append(a*c)
prod.append(a*d)
prod.append(b*c)
prod.append(b*d)

print(max(prod))