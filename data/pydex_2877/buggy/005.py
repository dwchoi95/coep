# compile-errors:success: Compilation Successful #
# compile-result:1 #
# save-event:compile #
N = str(input())
li=N.split()
c=0
for i in range(len(li)):
    c = li[i]
    if len c>=2 and c[0]==c[-1]:
        c+=1
print(c)