A=input() 
B=input() 
C=input() 

i=0
j=-1
k=-1
c=0

while(True):
    if(c==0):
        if(i>=(len(A))):
            print("A")
            exit()
        if(A[i]=="a"):
            i+=1
            c=0
        elif(A[i]=="b"):
            j+=1
            c=1
        else:
            k+=1
            c=2

    elif(c==1):
        if(j>=(len(B))):
            print("B")
            exit()
        if(B[j]=="a"):
            i+=1
            c=0
        elif(B[j]=="b"):
            j+=1
            c=1
        else:
            k+=1
            c=2
    else:
        if(k>=(len(C))):
            print("C")
            exit()
        if(C[k]=="a"):
            i+=1
            c=0
        elif(C[k]=="b"):
            j+=1
            c=1
        else:
            k+=1
            c=2


    

