# compile-errors:success: Compilation Successful #
# compile-result:1 #
# save-event:compile #
a=str(input())
b=(a.find('not',0,len(a)))
c=(a.find('bad',0,len(a)))
if b<c and b!=-1 and c!=-1:
    print(a.replace(a[b:c+3],'good',))
  else:
      print(a)
