# compile-errors:success: Compilation Successful #
# compile-result:1 #
# save-event:compile #
N=int(input())
r=[]
s=[]
m=[]
y=[]
i=[1]
while i<=N:
    t=0
    z=str(input())
    k=z.replace(' ','' )
    d=k.split(',',)
    if d[0]+' # '+d[1] in s:
        q=s.index(d[0]+' # '+d[1])
        t=int(m[q]+int(d[2])
        m[q]=t
    else:
        s.append(d[0]+' # '+d[1])
        m.append(d[2])
    i=i+1
x=0
while x<len(s):
    f=s[x]=' # '+str(m[x])
    y.append(f)
    y.sort()
    x=x+1
h=0
while h<len(y):
    print(y[h])
    h=h+1