# compile-errors:success: Compilation Successful #
# compile-result:1 #
# save-event:compile #
num=int(input())
test_num=str(num)
print("Reverse:",int(test_num[::-1]))
print("Sum:",(num+int(test_num[::-1]))