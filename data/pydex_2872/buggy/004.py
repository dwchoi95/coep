# compile-errors:success: Compilation Successful #
# compile-result:1 #
# save-event:compile #
v=str(input())
k=(v.find('not',Î¸,len(v)))
l=(v.find('bad',Î¸,len(v)))
if k<l and k!=-1 and l!=-1:
    print(v.replace(v[k:l+3],'good', ))
else:
    print(v)
    