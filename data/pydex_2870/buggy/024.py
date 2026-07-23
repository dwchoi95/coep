# compile-errors:success: Compilation Successful #
# compile-result:1 #
# save-event:compile #
txt = str(input())

rev = txt.lower([::-1])
if(rev == txt):
    print(txt,' is a palindrome.')
else:
    print(txt,' is NOT a palindrome.')