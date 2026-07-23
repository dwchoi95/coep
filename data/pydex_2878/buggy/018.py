# compile-errors:success: Compilation Successful #
# compile-result:1 #
# save-event:compile #
t=int(input())
total=[]
for t in range(1,t+1):
    line=input()
    student=line.split(',')
    total.append(student)
    
marks={}
for x in total:
    if int(x[0]) not in marks:
        marks(int(x[0]))=int(x[2])
    else:
        y=int(x[2])
        marks[int(x[0])]+=y
for x in sorted(marks):
    print(str(x)+":"+str(marks[x]))