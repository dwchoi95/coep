# compile-errors:success: Compilation Successful #
# compile-result:1 #
# save-event:compile #
num=input()
a=int(num)
Sum=0
while a > 0 :
    digit=a%10
    Sum=Sum+digit**3
    a=a//10
if int(num)==int(Sum):
    print('Sum of Cubes is {}. It is the same as the number {}.'.format(Sum,num))
else:
    print('Sum of Cubes is {}. It is NOT same as the number {}.'.format(Sum,num)