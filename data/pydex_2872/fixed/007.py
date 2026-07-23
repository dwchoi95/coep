# compile-errors:success: Compilation Successful #
# compile-result:1 #
# save-event:compile #
x = str(input())
search_not = x.find('not')
search_bad = x.find('bad')
if search_not < search_bad:
    x1 = x.replace(x[search_not:(search_bad+3)], 'good')
    print(x1)
else:
    print(x)
