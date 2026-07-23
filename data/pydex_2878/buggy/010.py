# compile-errors:success: Compilation Successful #
# compile-result:1 #
# save-event:compile #
N = int(input())
r = []
s = []
m = []
i = 1
while i <= N:
    t = 0
    z =str(input())
    k =z.replace(' ','',)
    d =k.split(',',)
    id d[0] in r:
        if d[0] + d[1] in s:
            t=t
        else:
            s.append(d[0]+d[1])
            q=r.index(d[0])
            t =int(m[q]+int(d[2]))
            m[q]=t
    else:
        r.append(d[0])
        s.append(d[0]+d[1])
        m.append(int(d[2]))
    i =i+1
x=0
while x<len(r):
    f=r[x]+':'+str(m[x])
    f1=f.replace(' ','',)
    print(f1)
    x=x+1