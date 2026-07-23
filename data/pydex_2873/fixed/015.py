# compile-errors:success: Compilation Successful #
# compile-result:1 #
# save-event:compile #
num = int(input())
sum = 0
temp = num
while temp > 0:
    digit = temp % 10
    sum += digit ** 3
    temp //=10
    
if num == sum:
    print("Sum of Cubes is ", num ,". It is the same as the number ", num ,".", sep='')
else:
    print("Sum of Cubes is ", sum ,". It is NOT same as the number ", num ,".", sep='')