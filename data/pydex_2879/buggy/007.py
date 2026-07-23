# compile-errors:success: Compilation Successful #
# compile-result:1 #
# save-event:compile #
N = int(input())
total=[]
for i in range(1,N+1):
    line =input()
    student =line.split(',')
    total.append(student)

markssum = []
for i in total:
    if int(i[0]) not in markssum:
        markssum =[int(i[0])]={}
        markssum =[int(i[0])][i[1].strip()]=int(i[2])
    elif i[1].strip() not in markssum[int(i[0])]:
        markssum[int(i[0])][i[1].strip()]=int(i[2])
    else:
        k =int(i[2])
        markssum[int(i[0])][i[1].strip()] += k
        
for i in sorted(markssum):
    for j in sorted(markssum[i]):
        print(str(i)+'#'+j+'#'+ str(markssum[i][j]))