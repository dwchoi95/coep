# compile-errors:success: Compilation Successful #
# compile-result:1 #
# save-event:compile #
a = input()
b = a.find('not')
c = a.find('bad')
if c>b:
    x = a[b:c+3]
    print(a.replace(x, 'good'))
else:
        print(a)