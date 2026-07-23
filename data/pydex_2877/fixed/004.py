# compile-errors:success: Compilation Successful #
# compile-result:1 #
# save-event:compile #
x = input().split(',')
y = 0
for z in range (len(x)):
    p = x[z]
    if len(p)>=2 and p[0] == p[-1]:
        y += 1
print(y)