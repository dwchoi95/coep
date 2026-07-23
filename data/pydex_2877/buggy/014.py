# compile-errors:success: Compilation Successful #
# compile-result:1 #
# save-event:compile #
string=(input())
list=string.split(',')
count=0
for i in range(0,len(list)):
    ctr=list[i]
    if len(ctr)>=2 and ctr[0]==ctr[-1]:
    count+=1
print(count)