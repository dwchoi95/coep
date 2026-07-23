# compile-errors:success: Compilation Successful #
# compile-result:1 #
# save-event:compile #
str = input()
x = str.find('not')
y = str.find('bad')
if y>x:
    str=str.replace(str[x:(y+3)], 'good')
    print(str)
else:
    print(str)