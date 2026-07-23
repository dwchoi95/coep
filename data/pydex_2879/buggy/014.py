# compile-errors:success: Compilation Successful #
# compile-result:1 #
# save-event:compile #
i=str(input())
m=i.split(\n,)
N=int(m[0])
k=1
while k<N-1:
    a=m[k]
    a=a.strip()
    b=m.split(',',)
    print(b)
    k=k=1