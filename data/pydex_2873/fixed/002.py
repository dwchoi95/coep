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
    print("Sum of Cubes is {}. It is the same as the number {}." .format(j,i))
else:
        print("Sum of Cubes is {}. It is NOT same as the number {}." .format(j,i))