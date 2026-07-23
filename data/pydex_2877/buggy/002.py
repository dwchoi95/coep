# compile-errors:success: Compilation Successful #
# compile-result:1 #
# save-event:compile #
inp = input().split(',')
count = 0
for i in range(len(inp)):
    ctr = inp[i]
    l = len(ctr)
    print(type(ctr))
    if l>=2 and ctr[] == ctr[-1]:
        count+=1
print(count)