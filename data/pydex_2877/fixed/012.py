# compile-errors:success: Compilation Successful #
# compile-result:1 #
# save-event:compile #
strInput=input()
counter=0
listInput=strInput.split(',')
for i in range(0,len(listInput)):
    lstring=listInput[i]
    if(len(lstring)>=2):
        if lstring[0]==lstring[(len(lstring)-1)]:
            counter=counter+1
print(counter)
