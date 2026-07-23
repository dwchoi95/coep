# compile-errors:success: Compilation Successful #
# compile-result:1 #
# save-event:compile #
a = int(input())
total = []
for i in range(1,a+1):
    line = input()
    student = line.split(',')
    total.append(student)
sumofmarks = {}
for i in total:
    if int(i[0]) not in sumofmarks:
        sumofmarks[int(i[0])] = {}
        sumofmarks[int(i[0])][i[1].strip()]=int(i[2])
    elif i[1].strip() not in sumofmarks[int(i[0])]:
        sumofmarks[int(i[0])][i[1].strip()] = int(i[2])
    else:
        k = int(i[2])
        sumofmarks[int(i[0])][i[1].strip()+= k
    