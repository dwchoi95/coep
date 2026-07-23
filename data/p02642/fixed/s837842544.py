n=int(input(""))
aa=input("").split(" ")
lista=[]
for i in range(n):
    lista+=[int(aa[i])]
lista.sort()
listtf=[]
s=0
for i in range(lista[n-1]):
    listtf+=[True]
for i in range(n):
    
    if(listtf[lista[i]-1]):
        if(i<n-1 and lista[i]==lista[i+1]):
            s-=1
        s+=1
        t=1
        while(t*lista[i]<=lista[n-1]):
            listtf[lista[i]*t-1]=False
            t+=1
print(s)
            
            
        
        
    
