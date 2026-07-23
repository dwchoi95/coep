# compile-errors:success: Compilation Successful #
# compile-result:1 #
# save-event:compile #
import string 
string = input().split()  
def ispangram(str): 
    alphabet = "abcdefghijklmnopqrstuvwxyz"
    for char in alphabet: 
        if char not in str.lower(): 
            return False
  
    return True

if(ispangram(string) == True): 
    print("Yes, the string is a pangram.") 
else: 
    print(f"No, the string is NOT a pangram. Missing letter(s) is(are) {}") 