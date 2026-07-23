# compile-errors:success: Compilation Successful #
# compile-result:1 #
# save-event:compile #
a = int(input())
b = str(a)
d = b[ ::-1]
print('Reverse:',int(d))
S= a+int(d)
print('Sum:',S)