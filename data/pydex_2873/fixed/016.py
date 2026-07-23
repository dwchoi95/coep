# compile-errors:success: Compilation Successful #
# compile-result:1 #
# save-event:compile #
x = int(input())
y = str(x)
z = len(y) - 1
Sum = 0
while z >= 0:
    a = y[z:z+1]
    b = int(a)
    Sum += b**3
    z = z - 1
if x ==Sum:
    print('Sum of Cubes is ' + str(Sum) + '. It is the same as the number ' + y + '.')
else:
    print('Sum of Cubes is ' + str(Sum) + '. It is NOT same as the number ' + y + '.')