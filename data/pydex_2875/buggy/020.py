# compile-errors:success: Compilation Successful #
# compile-result:1 #
# save-event:compile #
Initial_Input = int(input())
Alphabetlist =  ["a","b","c","d","e","f","g","h","i","j","k","l","m","n","o","p","q","r","s","t","u","v","w","x","y","z"]
BigAlpha = [x.upper() for x in Alphabetlist] 
# Outer loop
for int(Initial_Input) in range(1,27):
    for i in range(0,Initial_Input):
            # inner loop
        for j in range(0,i+1):
            print('_'+ BigAlpha[j], end='')
    print('_')