# compile-errors:success: Compilation Successful #
# compile-result:1 #
# save-event:compile #
w=input()
if 97<ord(w[0])<122:
   rev_word=w[::-1]
   if w==rev_word:
        print(w,"is a palindrome")
   else:
        print(w,"is not a palindrome")
else:
    w[0]=chr(ord(w[0])+32)
    rev_word=w[::-1]
    if w==rev_word:
        print(w,"is a palindrome")
   else:
        print(w,"is not a palindrome")