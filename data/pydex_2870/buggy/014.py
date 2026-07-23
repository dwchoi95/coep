# compile-errors:success: Compilation Successful #
# compile-result:1 #
# save-event:compile #
a=input()
b=a.casefold()
reverse=b[::-1]
if b==reverse:
    print(a,"is a palindrome")
else
    print(a,"is NOT a palindrome")