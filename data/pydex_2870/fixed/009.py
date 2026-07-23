# compile-errors:success: Compilation Successful #
# compile-result:1 #
# save-event:compile #
suv = str(input())
s = suv.lower()
pt = s [::-1]
if(pt == s):
    print(suv,'is a palindrome.')
else:
    print(suv,'is NOT a palindrome.')