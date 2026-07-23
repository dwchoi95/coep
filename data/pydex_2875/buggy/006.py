# compile-errors:success: Compilation Successful #
# compile-result:1 #
# save-event:compile #
N = int(input())
for i in range(0,N):
    print("_")
    for j in range(0,i+1):
        ch=chr(j+65)
        print(ch,"_",<end="",sep="")
    print("\r")