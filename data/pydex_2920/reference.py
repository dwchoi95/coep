import string

alphabet = set(string.ascii_lowercase) 
  
def ispangram(s): 
    schar = set(s.lower())
    return (schar >= alphabet, sorted(list(alphabet - schar)))
      
# Driver code 
s = input()
flag, missing = ispangram(s)
if flag:
    print("Yes, the string is a pangram.") 
else: 
    misstr = ", ".join(missing)
    print("No, the string is NOT a pangram. Missing letter(s) is(are) {}.".format(misstr)) 
    
