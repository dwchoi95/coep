# compile-errors:success: Compilation Successful #
# compile-result:1 #
# save-event:compile #
name = input()
a = name.casefold()
reverse = a [::-1]
if(reverse == a):
    print(name,'is a palindrome.')
else:
    print(name,'is NOT a palindrome.')