# compile-errors:success: Compilation Successful #
# compile-result:1 #
# save-event:compile #
inp = input().split(',')
cnt = 0
for i in range(len(inp)):
    ctr = inp[i]
    if len(ctr)>=2 and ctr[0] == ctr[-1]:
        cnt+=1
print(cnt)