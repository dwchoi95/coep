a=input()
b=input()
c=input()





n='a'
while True:
    
    if n=='a':
        if len(a)==0:
            print('A')
            break
        else:
            n=a[0]
            a=a.lstrip(a[0])
    elif n=='b':
        if len(b)==0:
            print('B')
            break
        else:
            n=b[0]
            b=b.lstrip(b[0])
    else:
        if len(c)==0:
            print('C')
            break
        else:
            n=c[0]
            c=c.lstrip(c[0])

