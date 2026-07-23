# compile-errors:success: Compilation Successful #
# compile-result:1 #
# save-event:compile #
str=input()
str1=str[::-1]
if(str==str1)
    print(str,"is a palindrome.")
else:
    print(str,"is NOT a palindrome.")