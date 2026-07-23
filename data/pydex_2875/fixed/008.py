# compile-errors:success: Compilation Successful #
# compile-result:1 #
# save-event:compile #
if __name__ == '__main__': 
      
    n = int(input()) 
    for i in range(1, n + 1):
        print('_', end='')
        for j in range(1, i + 1): 
            print(chr(ord('A') + j - 1),  
                             end = "_"); 
  
        print(""); 
