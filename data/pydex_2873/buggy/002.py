# compile-errors:success: Compilation Successful #
# compile-result:1 #
# save-event:compile #
i = int(input())
j = 0
k = i
while k > 0:
    l = k % 10
    j = j + l ** 3
    k = k // 10
if i == j:
    print("Sum of Cubes is", j., "It is same as the number", i)
else:
        print("Sum of Cubes is", j., "It is NOT same as the number", i)