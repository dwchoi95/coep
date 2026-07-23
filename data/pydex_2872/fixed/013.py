# compile-errors:success: Compilation Successful #
# compile-result:1 #
# save-event:compile #
string=input()
idx1=string.find('not')
idx2=string.find('bad')
if idx2>idx1:
    str_st=string[:idx1]
    str_en=string[idx2+3:]
    print(str_st+"good"+str_en)
elif idx1==-1 or idx2==-1:
    print(string)
else:
    print(string)

