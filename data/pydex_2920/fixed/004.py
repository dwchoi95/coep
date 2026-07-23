# compile-errors:success: Compilation Successful #
# compile-result:1 #
# save-event:compile #
import string

imp = []

def check(text):
  global imp
  alphabet = set(string.ascii_lowercase)
  text = set(text)
  for i in alphabet:
    if i not in text:
      imp.append(i)
      
    
text = str(input())
check(text.lower())
imp.sort()

if len(imp) ==  0:
  print("Yes, the string is a pangram.")
else:
  print("No, the string is NOT a pangram. Missing letter(s) is(are)", end = "")
  for i in imp:
    if imp.index(i) == len(imp)-1:
      print(" {}". format(i), end = '.')
    else:
      print(" {}". format(i), end = ',')
  print('\n')