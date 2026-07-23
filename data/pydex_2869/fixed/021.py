# compile-errors:success: Compilation Successful #
# compile-result:1 #
# save-event:compile #
x = int(input())
y = str(x)
rev = y[::-1]
d = int(rev)
print('Reverse:',d )
k = int(x) + int(d)
print('Sum:', k)
