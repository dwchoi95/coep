# compile-errors:success: Compilation Successful #
# compile-result:1 #
# save-event:compile #
N=int(input())
total=[]

for i in range(1,N+1):
    line=input()
    student=line.split(',')
    print(student)
    total.append(student)

print()
marksSum={}
for i in total:
    print(i[0])
    if int(i[0]) not in marksSum:
         marksSum[int(i[0])]=int(i[2])
    else:
        k=int(i[2])
        print(k)
        marksSum[int(i[0])]=marksSum[int(i[0])+k
    

print()
print(marksSum)

