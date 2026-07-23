# compile-errors:success: Compilation Successful #
# compile-result:1 #
# save-event:compile #
txt = str(input())
k = txt.lower()
rev = k [::-1]
if(rev == k):
    print(txt,'is a palindrome.')
else:
    print(txt,'is NOT a palindrome.')