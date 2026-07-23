# compile-errors:success: Compilation Successful #
# compile-result:1 #
# save-event:compile #
name=input()
x= name.casefold()
if (x==x[::-1]):
    print(name , 'is a palindrome.')
else :
    print(name , 'is NOT a palindrome.')