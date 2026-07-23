# compile-errors:success: Compilation Successful #
# compile-result:1 #
# save-event:compile #
N=int(input())
total=[]

for i in range(1,N+1):
    line=input()
    student=line.split(',')
    total.append(student)

print()
print(total)
marksSum={}

for i in total:
    if int(i[0]) not in marksSum:
        marksSum[int(i[0])]={}
        marksSum[int(i[0])][i[1].strip()]=int(i[2])
        
    else print(i[1].strip,i[0])
        

print()
print(marksSum)

if 'CS102' in marksSum[101]:
    print("YEs")
else:
    print("No")