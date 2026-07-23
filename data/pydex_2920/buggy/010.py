# compile-errors:success: Compilation Successful #
# compile-result:1 #
# save-event:compile #
x = input()
x=set(x)
alphabet = set("abcdefghijklmnopqrstuvwxyz")
op = alphabet - x
if len(alphabet-x) != 0: 
    print('No, the string is NOT a pangram. Missing letter(s) is(are) ',", ".join(str(e) for e in op,'.'))
else:
    print('Yes, the string is a pangram.')