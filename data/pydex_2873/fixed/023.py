# compile-errors:success: Compilation Successful #
# compile-result:1 #
# save-event:compile #
num = int(input())
sum = 0
# find the sum of the cube of each digit
x = num
while x > 0:
   digit = x % 10
   sum += digit ** 3
   x //= 10
if num == sum:
   print("Sum of Cubes is {}. It is the same as the number {}.".format(sum,num))
else:
   print("Sum of Cubes is {}. It is NOT same as the number {}.".format(sum,num))
