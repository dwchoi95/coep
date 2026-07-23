# compile-errors:success: Compilation Successful #
# compile-result:1 #
# save-event:compile #
word=input()
if word.lower()==word[::-1].lower():
    print(word,"is a palindrome.")
else:
    print(word,"is NOT a palindrome.")
