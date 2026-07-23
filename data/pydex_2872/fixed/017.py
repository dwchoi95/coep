# compile-errors:success: Compilation Successful #
# compile-result:1 #
# save-event:compile #
string = input()

index_not = string.find('not')
index_bad = string.find('bad') + 3

if (index_bad < index_not) or (index_bad and index_not == -1):
    print(string)
else:
    substring = string[index_not:index_bad]
    result = (string.replace(substring,'good'))
    print(result)