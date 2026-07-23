# compile-errors:success: Compilation Successful #
# compile-result:1 #
# save-event:compile #
num=(input())
sum=0
for i in num:
    sum+=int(i)**3
if sum==int(num):
    print("Sum of Cubes is {}. It is the same as the number {}.".format(sum,num))
else:
    print("Sum of Cubes is {}. It is NOT same as the number {}.".format(sum,num))
    