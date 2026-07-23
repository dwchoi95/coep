# compile-errors:success: Compilation Successful #
# compile-result:1 #
# save-event:compile #
a = int(input())
total = []

for i in range (1,a+1):
    line = input()
    stu = line.split(',')
    total.append(stu)
    
m_sum = {}

for i in total:
    if int(i[0]) not in m_sum:
        m_sum[int(i[0])]={}
        m_sum[int(i[0])][i[1].strip()]=int(i[2])
        
    elif i[1].strip() not in m_sum[int(i[0])]:
        m_sum[int(i[0])][i[1].strip()]=int(i[2])
    else:
        k=int(i[2])
        m_sum[int(i[0])][i[1].strip()]+=k

for i in sorted(m_sum):
    for j in sorted(m_sum[i]):
        print(str(i)+" # "+j+" # "+str(m_sum[i][j]))
