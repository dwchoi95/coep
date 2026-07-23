# compile-errors:success: Compilation Successful #
# compile-result:1 #
# save-event:compile #
import string
missing = []
def check(inp):
  global missing
  alphabet = set(string.ascii_lowercase)
  inp = set(inp)
  for i in alphabet:
    if i not in inp:
      missing.append(i)
      
inp = str(input())
check(inp.lower())
missing.sort()

if len(missing) == 0:
  print("Yes, the string is a pangram.")
else:
  print("No, the string is NOT a pangram. Missing letter(s) is(are)", end = "")
  for i in missing:
    if missing.index(i) == len(missing)-1:
      print(" {}". format(i), end = '.')
    else:
      print(" {}". format(i), end = ',')
  print('\n')