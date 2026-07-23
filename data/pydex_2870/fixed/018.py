# compile-errors:success: Compilation Successful #
# compile-result:1 #
# save-event:compile #
string=str(input())
x=string.casefold()
if(x==x[::-1]):
    print(string, "is a palindrome.")
else:
    print(string, "is NOT a palindrome.")