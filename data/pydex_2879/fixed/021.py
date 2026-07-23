# compile-errors:success: Compilation Successful #
# compile-result:1 #
# save-event:compile #
initial_input = int(input())
total = []

for i in range(1, initial_input+1):
    line = input()
    student = line.split(',')
    total.append(student)

Sums_of_Marks= {}

for i in total:
    if int(i[0]) not in Sums_of_Marks:
        Sums_of_Marks[int(i[0])] = {}
        Sums_of_Marks[int(i[0])][i[1].strip()] = int(i[2])
        
    elif i[1].strip() not in Sums_of_Marks[int(i[0])]:
        Sums_of_Marks[int(i[0])][i[1].strip()] = int(i[2])
    else: 
        k = int(i[2])
        Sums_of_Marks[int(i[0])][i[1].strip()]+= k

for i in sorted(Sums_of_Marks):
    for j in sorted(Sums_of_Marks[i]):
        print(str(i) + " # " + j + " # " + str(Sums_of_Marks[i][j]))
