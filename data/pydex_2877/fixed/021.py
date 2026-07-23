# compile-errors:success: Compilation Successful #
# compile-result:1 #
# save-event:compile #
a=str(input())
b=a.split(',')
k=len(b)
m=0
x=0
while m<k:
    n=b[m]
    if len(n)>=2 and n[0]==n[len(n)-1]:
        x=x+1
    else:
        x=x
    m=m+1
print(x)