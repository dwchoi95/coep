# compile-errors:success: Compilation Successful #
# compile-result:1 #
# save-event:compile #
string = input()
if(string.lower()==string.lower()[::-1]):
    print(string,'is a palindrome.')
else:
    print(string, 'is NOT a palindrome.')