# compile-errors:success: Compilation Successful #
# compile-result:1 #
# save-event:compile #
def returnmissingchar(x):
    global char
    a=''
    alp = "abcdefghijklmnopqrstuvwxyz"
    for i in range(len(alp)): 
        if alp[i] not in x.lower():
          a=a+', '+alp[i]
    a=a.replace(',','',1)
    return a     
def pangram(x): 
    alp = "abcdefghijklmnopqrstuvwxyz"
    for i in range(len(alp)): 
        if alp[i] not in x.lower(): 
            return False
    return True


          
      
      
x1=str(input())
k=returnmissingchar(x1)
if(pangram(x1) == True): 
    print("Yes, the string is a pangram.") 
else: 
    print("No, the string is NOT a pangram. Missing letter(s) is(are)"+k+'.'