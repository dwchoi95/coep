# compile-errors:success: Compilation Successful #
# compile-result:1 #
# save-event:compile #
p = str(input())
x = p.lower()
rev = x[::-1]
if(rev == x):
  print(p,"is a palindrome.")
else:
  print(p,"is NOT a palindrome.")