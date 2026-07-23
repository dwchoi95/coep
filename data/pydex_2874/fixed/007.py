# compile-errors:success: Compilation Successful #
# compile-result:1 #
# save-event:compile #
n=int(input())
for i in range(0,n):
    for j in range(0,i+1):
        print("*", end='')
    print()