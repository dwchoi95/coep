# compile-errors:success: Compilation Successful #
# compile-result:1 #
# save-event:compile #
x = int(input())
sum = 0
temp = x
while temp >0:
    digit = temp% 10
    sum += digit ** 3
    temp//= 10
if(x==sum):
    print('Sum of Cubes is',x, end=". ")
    print('It is the same as the number',x, end".")
else:
    print('Sum of Cubes is',sum,'. It is NOT same as the number',x,'.')