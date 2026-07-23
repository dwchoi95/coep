# compile-errors:success: Compilation Successful #
# compile-result:1 #
# save-event:compile #
N = int(input())
total = []

for i in range(1,N+1):
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
        sumofmarks[int(i[0])][i[1].strip()] += k
for i in sorted (sumofmarks):
    for j in sorted (sumofmarks[i]):
        print(str(i) + ' # ' +j+ ' # '+ str(sumofmarks[i][j]))