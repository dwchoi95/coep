# compile-errors:success: Compilation Successful #
# compile-result:1 #
# save-event:compile #
x=input()
data = []
dict = {}
for i in range(int(x)):
    data.append(input().split(','))
for a in data:
    keys= a[0]
    values=a[2]
    dict[keys] = dict.get(keys,0) + int(values)
for k in dict:
    print(k,dict[k], sep=':')