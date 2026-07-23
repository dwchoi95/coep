# compile-errors:success: Compilation Successful #
# compile-result:1 #
# save-event:compile #
num=int(input())#int type,to read only integers as input
test_num=str(num)#converting into string type,for indexing and reversal
print("Reverse:",int(test_num[::-1]))
print("Sum:",((num)+int(test_num[::-1])))