# compile-errors:success: Compilation Successful #
# compile-result:1 #
# save-event:compile #
n = input().split(",')
x = [y for y in n]
k = 0
for y in x:
    if len(y)>=2 and y[0]==y[len(y)-1: ]:
        k = k+1
print(k)