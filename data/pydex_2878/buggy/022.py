# compile-errors:success: Compilation Successful #
# compile-result:1 #
# save-event:compile #
a=input()
data=[]
dict={}
for i in range((int(a)))
    data.append(input().split(','))
for x in data:
    keys=x[0]
    values=x[2]
    dict[keys]=dict.get(keys,0) + int(values)
for k in dict:
    print(k,dict[k],sep='.')