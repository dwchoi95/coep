# compile-errors:success: Compilation Successful #
# compile-result:1 #
# save-event:compile #
n = input()
count = 0
split_n = n.split(',')
for i in split_n:
    if len(i)>= 2:
        if (tuple(i)[0] == tuple(i)[-1], end=''):
            count = count+1
            print(count)