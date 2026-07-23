# compile-errors:success: Compilation Successful #
# compile-result:1 #
# save-event:compile #
x = int(input())
a=str(x)[::-1]
a=int(a)
print('Reverse: ', a)
sum = x+a
print(\n'sum: ',sum)