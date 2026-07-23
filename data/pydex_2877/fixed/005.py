# compile-errors:success: Compilation Successful #
# compile-result:1 #
# save-event:compile #
N = str(input())
li = N.split(',')
c=0
for i in range(len(li)):
    ctr = li[i]
    if len(ctr)>=2 and ctr[0]==ctr[-1]:
        c+=1
print(c)