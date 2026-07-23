# compile-errors:success: Compilation Successful #
# compile-result:1 #
# save-event:compile #
N = int(input())
total=[]
for i in range (1,N+1):
    line=input()
    student=line.split(',')
    total.append(student)
marksSum={}
for i in total:
    if int(i[0])not in marksSum:
        marksSum[int(i[0])]= int(i[2])
    else:
        k=int(i[2])
        marksSum[int(i[0])]+=k
for i in sorted(marksSum):
    print(str(i)+":"+str(marksSum[i]))