# compile-errors:success: Compilation Successful #
# compile-result:1 #
# save-event:compile #
n=input()
sum=0
for i in n:
    cube=int(i)**3
    sum +=cube
if int(n)==sum:
    print("Sum of Cubes is {}. It is the same as the number {}.".format(sum,n))
else:
    print("Sum of Cubes is {}. It is NOT same as the number {}.".format(sum,n))