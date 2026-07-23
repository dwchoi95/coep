# compile-errors:success: Compilation Successful #
# compile-result:1 #
# save-event:compile #
n= int(input())
for i in range(65,n+65):
    for j in range(65,i+1):
        print(end="_",chr(j),end="_")
    print()