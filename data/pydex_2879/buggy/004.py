# compile-errors:success: Compilation Successful #
# compile-result:1 #
# save-event:compile #
N = int(input())
Total = []

for i in range (1,N+1):
    line= input()
    student=line.split(',')
    Total.append(student)
    
    marksSum={}
    
    for i in Total:
        if int([0]) not in marksSum:
            marksSum[(i[0]={}
            marksSum[int(i[0])][i[1].strip()]=int(i[2])
            
        elif i[1].strip() not in marksSum[int(i[0])]:
            marksSum[int(i[0])][i[1].strip()]=int(i[2])
        else:
            k=int(i[2])
            marksSum[int(i[0])][i[1].strip()]+=k
for i in sorted(marksSum):
    for j in sorted(marksSum[i]):
        print(str(i)+" # "+j+" # "+str(marksSum[i][j]))
        
        