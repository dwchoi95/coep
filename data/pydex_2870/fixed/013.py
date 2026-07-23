# compile-errors:success: Compilation Successful #
# compile-result:1 #
# save-event:compile #
x = str(input())
y = x.casefold()
if y == y[::-1]:
    print(x,'is a palindrome.')
else:
    print(x, 'is NOT a palindrome.')