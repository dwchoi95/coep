# compile-errors:success: Compilation Successful #
# compile-result:1 #
# save-event:compile #
n=int(input())
count,sum=0,0
while(n>0):
    digit=n%10
    sum=sum + digit^3
    digit=digit%10
if(sum==n):
    print('Sum of Cubes is',sum,'.','It is the same as the number',n)
 else:
    print('Sum of Cubes is',sum,'.','It is NOT same as the number',n)