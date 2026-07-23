# compile-errors:success: Compilation Successful #
# compile-result:1 #
# save-event:compile #
n =int(input())
alphabet = ["A","B","C","D","E","F","G","H","I","J","K","L","M","N","O","P","Q","R","S","T","U","V","W","X","Y","Z"]
if 1<=n<=26:
#outerloop
    for i in range(0,n):
#innerloop
        for j in range(0,i+1):
            print('_'+ alphabet[j], end='')
        print('_')