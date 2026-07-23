# compile-errors:success: Compilation Successful #
# compile-result:1 #
# save-event:compile #
N = int(input())
total=[]

for i in range(1,N+1):
    line=input()
    student=line.split(',')
    total.append(student)
    
marksSum={}

for i in total:
    if int(1[0]) not in marksSum:
        marksSum[int(i[0])]={}
        marksSum[int(i[0])][i[1].strip()]=int(i[2])
        
    elis i[1].strip() not in marksSum[int(i[0])]:
        marksSum[int(i[0])][i[1].strip()]=int(1[2])
    else:
        k=int(i[2])
        marksSum[int(1[0])][i[1].strip()]+=k
        
for i in sorted(marksSum):
    for j in sorted(marksSum[i]):
        print(str(i)+" # "+" # " + str(marksSum[i][j]))