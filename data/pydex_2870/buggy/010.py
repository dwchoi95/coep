# compile-errors:success: Compilation Successful #
# compile-result:1 #
# save-event:compile #
Word=input()
x=Word.lower()
If(x==x[::-1]):
    print(Word,"is a palindrome.")
else:
    print(Word,"is NOT a palindrome.")