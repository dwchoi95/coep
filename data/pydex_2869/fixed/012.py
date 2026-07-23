# compile-errors:success: Compilation Successful #
# compile-result:1 #
# save-event:compile #
first_number=int(input())
ffirst_number=str(first_number)
second_number=ffirst_number[::-1]
i_number=int(second_number)
print('Reverse:',i_number)
addn=(first_number + i_number)
print('Sum:',addn)
