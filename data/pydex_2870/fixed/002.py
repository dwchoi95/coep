# compile-errors:success: Compilation Successful #
# compile-result:1 #
# save-event:compile #
S = input()
if(S.lower()==S.lower()[::-1]):
        print(S,'is a palindrome.')
else:
        print(S,'is NOT a palindrome.')