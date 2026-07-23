# compile-errors:success: Compilation Successful #
# compile-result:1 #
# save-event:compile #
def IsPrime(x):
    count=0
    for i in range(1,sqrt(x)+1):
        if((x%i)==0):
            count++
    if (count==2):
        return true
    else:
        return false
        
if IsPrime(5):
    print("Hello")