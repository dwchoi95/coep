# compile-errors:success: Compilation Successful #
# compile-result:1 #
# save-event:compile #
a=str(input())
m=a.casefold()
x=m[ : :-1]
if m==x: 
    print(a,'is a palindrome.')
else: print(a,'is NOT a palindrome.')
