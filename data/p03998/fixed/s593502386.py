a=input()
b=input()
c=input()





n='a'
while True: 
    if n=='a':
        if len(a)==0:
            print('A')
            exit()
            
        n=a[0]
        
        a=a[1:]
        
    elif n=='b':
        if len(b)==0:
            print('B')
            exit()
            
        n=b[0]
        
        b=b[1:]
        
    else:
        if len(c)==0:
            print('C')
            exit()
            
        n=c[0]
        
        c=c[1:]

