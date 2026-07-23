# compile-errors:success: Compilation Successful #
# compile-result:1 #
# save-event:compile #
a = int(input())
for i in range(0, a):
    for j in range(0, i + 1):
        print("*", end='')
    print("\")