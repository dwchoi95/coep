# compile-errors:success: Compilation Successful #
# compile-result:1 #
# save-event:compile #
index = input()

if index.lower() == index[::-1].lower():
    print(index,'is a palindrome.')
else:
    print(index,'is NOT a palindrome. ')