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
        marks[int(x[0])]={}
        marks[int(x[0])][x[1].strip()]=int(x[2])
        
    elif x[1].strip() not in marks:[int(x[0])]:
        marks[int(x[0])][x[1].strip()]=int(x[2])
for x in sorted(marks):
    for y in sorted(marks[x]):
        print(str(x)+" # "+y+" # "+str(marks[x][y]))
print()