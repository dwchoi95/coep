# compile-errors:success: Compilation Successful #
# compile-result:1 #
# save-event:compile #
n = input()
sum = 0
t=int(n)
while (t>0):
    sum = sum + (t%10)**3
    t = t//10
if int(n) == int(sum) :
    print('Sum of Cubes is {}. It is the same as the number {}.'.format(sum,n))
else:
    print('Sum of Cubes is {}. It is NOT same as the number {}.'.format(sum,n))