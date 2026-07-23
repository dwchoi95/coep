# compile-errors:success: Compilation Successful #
# compile-result:1 #
# save-event:compile #
String_Input = input()
K = 0
listinput =String_Input.split(',')
for i in range(0,len(listinput)):
    StringList =listinput[i]
    if(len(StringList)>=2):
        flag =0
        if StringList[0] == StringList[len(StringList)-1]:
            K = K+1
print (K)