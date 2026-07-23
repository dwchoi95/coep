o=input()
e=input()
for i,j in zip(o,e):
    print(i+j,end="")
if len(o)!=len(e):print(o[-1:])