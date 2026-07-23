# compile-errors:success: Compilation Successful #
# compile-result:1 #
# save-event:compile #

n=input()
m=n[::-1]
if(n.casefold()==m.casefold()):
    print('{} is a palindrome.'.format(n))
else:
    print('{} is NOT a palindrome.'.format(n))