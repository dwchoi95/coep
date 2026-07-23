# compile-errors:success: Compilation Successful #
# compile-result:1 #
# save-event:compile #
x = input()
y = x.lower()
if(y == y[::-1]):
    print(x, "is a palindrome.")
    else:
        print(x, "is not a palindrome.")