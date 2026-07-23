# compile-errors:success: Compilation Successful #
# compile-result:1 #
# save-event:compile #
global a=''
def returnmissingchar(x):
    global char
    alp = "abcdefghijklmnopqrstuvwxyz"
    for i in range(len(alp)): 
        if alp[i] not in x.lower():
          a=a+','+char
    a.lstrip(',')      
def pangram(str): 
    alp = "abcdefghijklmnopqrstuvwxyz"
    for i in range(len(alp)): 
        if alp[i] not in x.lower(): 
            return False
    return True


          
      
      
x1=input()
returnmissingchar(x1)
if(pangram(x1) == True): 
    print("Yes, the string is a pangram.") 
else: 
    print("No, the string is NOT a pangram. Missing letter(s) is(are)",a+'.')