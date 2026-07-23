# compile-errors:success: Compilation Successful #
# compile-result:1 #
# save-event:compile #
str1=input()
str2=str1.find('not')
str3=str1.find('bad')
name=str1[str2:str3+3:1]
final=str1.replace(name, "good")
if str3>str2:
    print(final)
    else:
        print(str1)