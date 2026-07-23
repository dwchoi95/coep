
n=int(input())
b=input()

b=b.split()

b=list(map(int,b))
a=list()
a.append(b[0])
a.append(b[0])
for i in range(1,len(b)-1):
    
    
    a.append(min(b[i],b[i+1]))
if(n>2):
    a.append(max(b[len(b)-1],a[len(a)-1]))
sum=0 
for i in range(len(a)):
    sum+=a[i]
print(sum)
