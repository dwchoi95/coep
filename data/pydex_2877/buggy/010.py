# compile-errors:success: Compilation Successful #
# compile-result:1 #
# save-event:compile #
n=input()
m=n.split(",")
l=len(m)
c=0
for i in range (0,l):
    n2=m[i]
#    print (n2)
    l2=len(n2)
#    print (l2)
    if l2>=2:
        c=c+1
    a=n2[0]
    b=n2[l2-1]
    print ("asd",a,b)
        if n2[0]==n2[l2-1]:
            c=c+1
print(c)