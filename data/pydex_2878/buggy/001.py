# compile-errors:success: Compilation Successful #
# compile-result:1 #
# save-event:compile #
a = input()
data = []
d = {}
for i in range((int(a))):
    data.append(input().split(',')
for x in data:
    keys = x[0]
    values = x[2]
    d[keys] = d.get(keys,0)+ int(values)
for k in d:
    print(k,d[k],sep='.')