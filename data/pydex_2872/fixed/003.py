# compile-errors:success: Compilation Successful #
# compile-result:1 #
# save-event:compile #
string=input()
wet_index=string.find("not")
hot_index=string.find("bad")+3


if(hot_index < wet_index or hot_index==(-1) or wet_index==(-1)):
    print(string)
else:
    substring=string[wet_index:hot_index]
    result=string.replace(substring, "good")
    print(result)