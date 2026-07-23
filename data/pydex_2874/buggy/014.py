# compile-errors:success: Compilation Successful #
# compile-result:1 #
# save-event:compile #
rows = 5
for i in range(0, rows):
    for j in range(0, i + 1):
        print("*", end=' ')

    print("\r")
    rows = 