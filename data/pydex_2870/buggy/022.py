# compile-errors:success: Compilation Successful #
# compile-result:1 #
# save-event:compile #
X = str(input())
if(X==X[::-1])
   print(X ,'is a palindrome.')
else:
    print(X ,'is not a palindrome.')