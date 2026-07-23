# compile-errors:success: Compilation Successful #
# compile-result:1 #
# save-event:compile #
number=int(input())
a=str(number)
a[::-1]
b=int(a[::-1])
print('Reverse:',b)
print('Sum:',number+b)