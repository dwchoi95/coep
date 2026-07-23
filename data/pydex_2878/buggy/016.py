# compile-errors:success: Compilation Successful #
# compile-result:1 #
# save-event:compile #
def sum_marks(1st):
    a=dict()
    for i in 1st:
        x=int(i[0])
        y=int(i[-1])
        if x in a:
            a[x]+=y
        else:
            b={x:y}
            a.update(b)
    return(a)
    
q=int(input())
r=1
1st=list()
while (r<=q):
    str=input()
    1st.append(str.split(','))
    r+=1
g=(sum_marks(1st))
L1=list()
for i in g:
    k=(i)
    l=(g[i])
    L1.append('{}:{}'.format(k,l))
L1.sort()
for i in L1:
    print(i)