import math
n=int(input(""))
aa=input("").split(" ")
lista=[]
for i in range(n):
    lista+=[int(aa[i])]
s=0
lista.sort()
listde=set()
for i in range(n-1):
    if(lista[i]==lista[i+1] ):
        listde.add(lista[i])
t=0
for i in range(n):
    t=0
    for k in listde:
        
        if (lista[i]%k==0):
            t=1
            break
    if (t==0):
        s+=1
        if(lista[i]<=math.sqrt(lista[n-1])):
            listde.add(lista[i])
print(s)
    
        
