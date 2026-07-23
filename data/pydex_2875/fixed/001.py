# compile-errors:success: Compilation Successful #
# compile-result:1 #
# save-event:compile #
i = int(input())
for x in range(1, i+1):
    print('_', end='')
    j = 65
    for y in range(1, x + 1):
        print(chr(j)+"_", end="")
        j = j + 1
    print()