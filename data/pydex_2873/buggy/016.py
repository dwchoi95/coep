# compile-errors:success: Compilation Successful #
# compile-result:1 #
# save-event:compile #
x = input()
y = str(x)
if x == int(y[0])**3+int(y[1])**3+int(y[2])**3:
    print('Sum of Cubes is', x,' It is the same as the number', x,'.')
else:
    z = int(y[0])**3+int(y[1])**3+int(y[2])**3
    print('Sum of Cubes is', y,' It is NOT same as the number',x'.')