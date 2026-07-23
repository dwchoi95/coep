# compile-errors:success: Compilation Successful #
# compile-result:1 #
# save-event:compile #
number=int(input())
k=str(number)
l=len(k)
s=0
p=1-1
while p>=0:
    j=k[p:p+1]
    i=int(j)
    s=s+i***3
    p=p-1
if s==number:
    print('sum of cubes is '+ str(s) +'. It is the same as the number '+ k +'.')
else:
    print('Sum of Cubes is '+ str(s) +'. It is NOT same as the number '+ k +'.')