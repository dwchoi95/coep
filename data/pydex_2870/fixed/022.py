# compile-errors:success: Compilation Successful #
# compile-result:1 #
# save-event:compile #
X = str(input())
Y = X.lower()
if(Y==Y[::-1]):
   print(X ,'is a palindrome.')
else:
    print(X ,'is NOT a palindrome.')