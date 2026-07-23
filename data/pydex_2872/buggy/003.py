# compile-errors:success: Compilation Successful #
# compile-result:1 #
# save-event:compile #
string=input()
not_index=string.find("not")
bad_index=string.find("bad")
bad_index=bad_index + 3

if(bad_index < not_index or bad_index==(-1) or not_index==(-1)):
print(string)
else:
substring=string[not_index:bad_index]
result=string.replace(substring, "good")
print(result)