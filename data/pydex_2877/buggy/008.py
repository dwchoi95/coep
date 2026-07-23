# compile-errors:success: Compilation Successful #
# compile-result:1 #
# save-event:compile #
n=input()
count=0
split_n = n.split(',')
for i in split_n:
    if (len(i)>= 2 and str(i)[0] == str(i)[-1]:
        count = count+1
print(count)