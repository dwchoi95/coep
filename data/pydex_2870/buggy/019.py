# compile-errors:success: Compilation Successful #
# compile-result:1 #
# save-event:compile #
str=input()
str1=str.casefold()
str2=str1[::-1]
if(str1)==(str2):
    print(str,"is a palindrome.")
 else:
    print(str,"is NOT a palindrome.")