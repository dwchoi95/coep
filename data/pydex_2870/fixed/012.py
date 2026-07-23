# compile-errors:success: Compilation Successful #
# compile-result:1 #
# save-event:compile #
a=str(input())
b=a.casefold()
c=b[::-1]
if b==c:
    print(a,'is a palindrome.')
else: print(a,'is NOT a palindrome.')