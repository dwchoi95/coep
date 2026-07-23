# compile-errors:success: Compilation Successful #
# compile-result:1 #
# save-event:compile #
def missingletter(j):
    global char
    y=''
    sample="abcdefghijklmnopqrstuvwxyz"
    for i in range(len(sample)): 
        if sample[i] not in j.lower():
          y=y+', '+sample[i]
    y=y.replace(',','',1)
    return y     
def pangram(j): 
    sample="abcdefghijklmnopqrstuvwxyz"
    for i in range(len(sample)): 
        if sample[i] not in j.lower(): 
            return False
    return True
k=str(input())
l=missingletter(k)
if(pangram(k) == True): 
    print("Yes, the string is a pangram.") 
else: 
    print("No, the string is NOT a pangram. Missing letter(s) is(are)"+l+'.')