# compile-errors:success: Compilation Successful #
# compile-result:1 #
# save-event:compile #
new=str(input())
y=new.split(',')
l=len(y)
i=0
count=0
while i<l:
    a=y[i]
    if len(a)>=2 and a[0]==a[(len(a)-1]:
        count+=1
    else:
        count=count
    i=i+1
print(count)