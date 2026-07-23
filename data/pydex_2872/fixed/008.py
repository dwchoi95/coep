# compile-errors:success: Compilation Successful #
# compile-result:1 #
# save-event:compile #
n=input()
a=n.rfind('not')
b=n.rfind('bad')

if(a<b and a!=-1 and b!=-1):
    m=n[a:b+3]
    n=n.replace(m,'good')
    print(n)
else:
    print(n)