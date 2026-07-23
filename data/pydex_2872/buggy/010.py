# compile-errors:success: Compilation Successful #
# compile-result:1 #
# save-event:compile #
a=input()
index_not=a.find('not')
index_bad=a.find('bad')
if index_bad=-1 or index_not=-1 or index_not>index_bad:
    print(a)
else:
    b=a[:index_not]+'good'+a[index_bad+3:]
    print(b)