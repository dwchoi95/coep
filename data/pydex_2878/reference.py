records=int(input())
if records <= 0:
    exit()

Roll2Marks = dict()
for i in range(records):
    inp  = input().split(',')
    roll = int(inp[0])
    subj = inp[1].strip()
    marks= int(inp[2])
    #print(roll, subj, marks)
    Roll2Marks[roll] = Roll2Marks.get(roll, 0) + marks
    

for key in sorted(Roll2Marks.keys()):
    print(key, Roll2Marks[key], sep=':')