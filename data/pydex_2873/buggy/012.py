# compile-errors:success: Compilation Successful #
# compile-result:1 #
# save-event:compile #
n = int(input())
sum = 0
times = 0
t = n
while (t>0):
    times = times + 1
    t = t//10
t=n
while (t>0):
    sum = sum + (t%10)**times
    t = t//10
if t == sum :
    print('Sum of cubes is'{}'.It is the same as the number'{}'.'.format(sum,t))
else:
    print('Sum of cubes is'{}'.It is NOT same as the number'{}'.'.format(sum,t))