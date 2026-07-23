# compile-errors:success: Compilation Successful #
# compile-result:1 #
# save-event:compile #
import string
def ispangram(str):
    alphabet = "abcdefghijklmnopqrstuvwxyz"
    empt=''
    for char in alphabet:
        if char not in str.lower():
            char=char+', '
            empt=empt+char#space aayega comma ke baad
    return empt
   
# main
string = str(input().split())
empt=""
k=ispangram(string)
if(k ==empt):
  print("Yes, the string is a pangram.")
else:
    k=k[:len(k)-2)]
    k=k+'.'
    print("No, the string is NOT a pangram. Missing letter(s) is(are)",k)