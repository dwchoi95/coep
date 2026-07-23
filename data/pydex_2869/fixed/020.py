# compile-errors:success: Compilation Successful #
# compile-result:1 #
# save-event:compile #
INPUT=int(input())
STRING=str(INPUT)
print('Reverse:',int(STRING[::-1]))
print('Sum:',((INPUT)+int(STRING[::-1])))

