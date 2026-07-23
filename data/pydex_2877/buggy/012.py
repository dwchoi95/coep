# compile-errors:success: Compilation Successful #
# compile-result:1 #
# save-event:compile #
strInput=input()
counter=0
print(strInput)
listInput=strInput.split(',')
for i in range(0,len(listInput)):
    lstring=listInput[i]
    if(len(lstring)>=2):
        flag=0
        for j in range(0,(len(lstring)//2):
            print("__",lstring[j],lstring[len(lstring)-1],"__")
            if lstring[j]!=lstring[len(lstring)-1]:
                flag=1
        if flag==1:
            counter=counter+1
            print(lstring)
print(counter)
