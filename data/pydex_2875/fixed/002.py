# compile-errors:success: Compilation Successful #
# compile-result:1 #
# save-event:compile #
num=int(input())

if num<=26 and num>=1:
    for i in range(1,num+1):
        j=0
        print("_", end="")
        while j<i:
            print(chr(65+j),end="_")
            j+=1
        print()