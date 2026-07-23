# compile-errors:success: Compilation Successful #
# compile-result:1 #
# save-event:compile #
asciiNumber = 65
N = int(input())
if(N>=1 and N<=26):
 for i in range(0, N):
     print("_",end='')
    for j in range(0, i + 1):
        character = chr(asciiNumber)
    
        asciiNumber += 2
    
        print(character + "_", end=' ')
        
    print(" ")
    