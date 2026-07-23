# compile-errors:success: Compilation Successful #
# compile-result:1 #
# save-event:compile #
x = str(input())
y = x.split(',')
z = len(y)
a = 0
b = 0
while b < z:
    i = y[b]
    if len(i) >= 2 and i[0] == i[len(i) - 1]:
        a = a + 1
    else:
        a = a
    b = b +1
print(a)