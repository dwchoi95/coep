# compile-errors:success: Compilation Successful #
# compile-result:1 #
# save-event:compile #
num = int(input())
n = str(num)

print('Reverse:', int(n[::-1]))
print('Sum:',num+int(n[::-1]))