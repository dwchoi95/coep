# compile-errors:success: Compilation Successful #
# compile-result:1 #
# save-event:compile #
n=int(input())
sum = 0
temp = n
while (temp > 0):
   digit = temp % 10
   sum += digit ** 3
   temp = temp// 10
if(sum==n):
    print('Sum of cubes is{}. It is same as the number{}.'.format(sum,n)
else:
    print('Sum of cubes is {}. It is NOT same as the number{}.'.format(sum,n)