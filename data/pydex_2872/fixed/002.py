# compile-errors:success: Compilation Successful #
# compile-result:1 #
# save-event:compile #
s1 = str(input())
search_not = s1.find('not')
search_bad = s1.find('bad')
if search_not < search_bad:
     s2 = s1.replace(s1[(search_not):(search_bad+3)], 'good')
     print(s2)
else: 
    print(s1)
