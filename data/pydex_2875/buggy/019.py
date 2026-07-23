# compile-errors:success: Compilation Successful #
# compile-result:1 #
# save-event:compile #
letter = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
i = 0
n = int(input())
for i in range(1,n+1):
    for j in range(1,i+1):
print('_',letter[i],end = '_')

