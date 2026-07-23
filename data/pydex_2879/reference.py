records=int(input())

Roll2Subj = dict()
for i in range(records):
    inp  = input().split(',')
    roll = int(inp[0])
    subj = inp[1].strip()
    marks= int(inp[2])
    if roll not in Roll2Subj:
        Roll2Subj[roll] = dict()
    
    Roll2Subj[roll][subj] = Roll2Subj[roll].get(subj, 0) + marks
    

for roll in sorted(Roll2Subj.keys()):
    subjects = sorted(Roll2Subj[roll].keys())
    for subj in subjects:
        print(roll, subj, Roll2Subj[roll][subj], sep=' # ')