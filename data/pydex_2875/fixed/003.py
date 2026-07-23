# compile-errors:success: Compilation Successful #
# compile-result:1 #
# save-event:compile #
n=int(input())
for i in range(0,n):
    for j in range(65,66+i):#using ASCII codes for Capital Alphabets
        print("_",chr(j),end="",sep="")
    print("_")
    
