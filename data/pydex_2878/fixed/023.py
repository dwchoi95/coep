# compile-errors:success: Compilation Successful #
# compile-result:1 #
# save-event:compile #
x = input()
d = []
dict = {}
for i in range((int(x))):
    d.append(input().split(','))
for y in d:
    keys=y[0]
    values=y[2]
    dict[keys]=dict.get(keys,0)+int(values)
for k in dict:
    print(k,dict[k],sep=':')








