# compile-errors:success: Compilation Successful #
# compile-result:1 #
# save-event:compile #
def sum(lst):
    a=dict()
    for i in lst:
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
lst = list()
while (r<=q):
    str=input()
    lst.append(str.split(','))
    r=r+1

g=(sum(lst))
l1=list()

for i in g:
    k=i
    l=g[i]
    l1.append('{}:{}'.format(k,l))

l1.sort()
for i in l1:
    print (i)