# compile-errors:success: Compilation Successful #
# compile-result:1 #
# save-event:compile #
N=int(input())
for i in range(N):
    for j in range(i+1):
        print("*",end="")
    print()
    