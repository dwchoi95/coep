# compile-errors:success: Compilation Successful #
# compile-result:1 #
# save-event:compile #
string = input()
silo = string.split(',')
count = 0
for i in silo:
    if len(i) >= 2 and i.endswith(i[0]):
    count += 1
print(count)