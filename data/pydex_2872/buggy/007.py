# compile-errors:success: Compilation Successful #
# compile-result:1 #
# save-event:compile #
s = str(input())
search_not = s.find("not)
search_bad = s.find("bad")
if search_not < search_bad:
    s1 = s.replace(s[search_not:(search_bad+3:)], "good")
    print(s1)
else:
    print(s)
