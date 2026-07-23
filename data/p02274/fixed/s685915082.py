


global cnt
cnt=0

def merge(A,left,mid,right):
    L=A[left:mid]
    R=A[mid:right]
    L.append(float("inf"))
    R.append(float("inf"))
    
    i=0
    j=0
    for k in range(left,right):
        global cnt
        if L[i]<=R[j]:
            A[k]=L[i]
            i=i+1
        else:
            A[k]=R[j]
            j=j+1
            cnt+=mid-left-i

def mergeSort(A,left,right):
    if left+1<right:
        mid=(int)((left+right)/2)
        mergeSort(A,left,mid)
        mergeSort(A,mid,right)
        merge(A,left,mid,right)

n=int(input())
S=list(map(int,input().split()))

mergeSort(S,0,n)
print(cnt)
