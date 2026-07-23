# compile-errors:success: Compilation Successful #
# compile-result:1 #
# save-event:compile #
a=str(input())
b=a.split(',')
k=len(a)
m=0
n=0
while m<k:
    n=b[m]
    if len(n)>=2 and n[0]==n[len(a)-1]:
        n=n+1
    else:
            n=n
        m=m+1
print(c)