# compile-errors:success: Compilation Successful #
# compile-result:1 #
# save-event:compile #
rows = int(input())
print("")
for i in range(1, rows + 1) :
    for j in range (1, i + 1) :
        print('*',end='')
    print()
    