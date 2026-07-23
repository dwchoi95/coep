# compile-errors:success: Compilation Successful #
# compile-result:1 #
# save-event:compile #
N = int(input())
for i in range(0,N):
    for j in range(0,i+1):
        ch=chr(j+65)
        print("_",ch,end="",sep="")
    print("_")