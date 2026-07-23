# compile-errors:success: Compilation Successful #
# compile-result:1 #
# save-event:compile #
a=int(input())
sum=0
copy_a=a
while(a!=0):
    int r=a%10
    sum=sum+r*r*r
    a=a/10
if(sum==copy_a):
    print("Sum of Cubes is {}. It is the same as the number {}.".format(sum,copy_a))
else:
    print("Sum of Cubes is {}. It is NOT same as the number {}.".format(sum,copy_a))