# compile-errors:success: Compilation Successful #
# compile-result:1 #
# save-event:compile #
str = (input('Ayush')

str = str.casefold()

rev_str = reversed(str)

if list(str) == list(rev_str):
   print(str, 'is a palindrome.')
else:
   print(str, 'is NOT a palindrome.')