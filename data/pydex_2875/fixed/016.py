# compile-errors:success: Compilation Successful #
# compile-result:1 #
# save-event:compile #
n=int(input())
i=0
for i in range(0,n):
    for j in range(0,i+1):
        if(j==0):
            print("_"+chr(65+j),end="_")
        else:
            print(chr(65+j),end="_")
    print('')

         
