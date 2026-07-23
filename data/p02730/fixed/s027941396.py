S=input()
N=len(S)
i=0
if((N-1)/2%2==1):
    while (i<=((N-1)/2-1)/2):
        if( (S[i]==S[int((N-1)/2-i-1)]) & (S[i]==S[int((N-1)/2+1+i)]) & (S[i]==S[int(N-1-i)]) ):
            i+=1
        else:
            break;
    if(i==int(((N-1)/2-1)/2+1)):
        print('Yes')
    else:
        print('No')
    
else:
    while (i<=(N-1)/4):
        if( (S[i]==S[int((N-1)/2-i-1)]) & (S[i]==S[int((N-1)/2+1+i)]) & (S[i]==S[int(N-1-i)]) ):
            i+=1
        else:
            break;
    if(i==int((N-1)/4+1)):
        print('Yes')
    else:
        print('No')