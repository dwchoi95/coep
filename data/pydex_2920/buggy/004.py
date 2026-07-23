# compile-errors:success: Compilation Successful #
# compile-result:1 #
# save-event:compile #
import string

rem = []

def check(txt):
  global rem
  alphabet = set(string.ascii_lowercase)
  txt = set(txt)
  for i in alphabet:
    if i not in txt:
      rem.append(i)
      
    
txt = str(input())
check(txt.lower())
rem.sort()

if len(rem) ==  0:
  print("Yes, the string is a pangram.")
else:
  print("No, the string is NOT a pangram. Missing letter(s) is(are)", end = "")
  for i in rem:
    if rem.index(i) == len(rem)-1:
      print(" {}". format(i), end = '.')
    else:
      print(" {}". format(i), end = ',')
  print('\n'