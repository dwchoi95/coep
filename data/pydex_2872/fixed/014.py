# compile-errors:success: Compilation Successful #
# compile-result:1 #
# save-event:compile #
str=input()
a=str.find('not')
b=str.find('bad')
if b>a:
    str=str.replace(str[a:(b+3)],'good')
    print(str)
else:
    print(str)