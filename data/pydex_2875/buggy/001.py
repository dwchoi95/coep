# compile-errors:success: Compilation Successful #
# compile-result:1 #
# save-event:compile #
i = int(input())
for x in range(65, 90):
    for y in range(65, x + 1):
        print(chr(y), end="")
    print("_{}_".format y)