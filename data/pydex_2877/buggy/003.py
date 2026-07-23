# compile-errors:success: Compilation Successful #
# compile-result:1 #
# save-event:compile #
s1 = str(input()
s2=s1.split(', ')
cnt = 0
for i in range(len(s2)):
    ctr = s2[i]
    if len(ctr)>=2 and ctr[0]==ctr[-1]:
        ctr+=1
print(cnt)
   
    