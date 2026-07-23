# compile-errors:success: Compilation Successful #
# compile-result:1 #
# save-event:compile #
def addMarks(tMarks):
    lst=dict()
    for i in tMarks:
        x=int(i[0])
        y=int(i[-1])
        if x in lst:
            lst[x]+=y
        else:
            b={x:y}
            lst.update(b)
    return(lst)
    
num=int(input())
tMarks=list()
for i in range(num):
    str=input()
    tMarks.append(str.split(','))
report=(addMarks(tMarks))
L1=list()
for i in report:
    k=(i)
    l=(report[i])
    L1.append('{}:{}'.format(k,l))
L1.sort()
for i in L1:
    print(i)