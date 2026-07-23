

import sys
input=sys.stdin.readline

def main():
    n,m=map(int,input().split())
    A=list(map(int,input().split()))
    cnt=0
    suma=sum(A)
    for i in range(n):
        if A[i]>=suma/(4*m):
            cnt+=1
    if cnt>=m:
        print("Yes")
    else:
        print("No")
    
    
    
if __name__=="__main__":
    main()
