from itertools import combinations

def getval():
    n,k = map(int,input().split())
    a = list(map(int,input().split()))
    return n,k,a

def main(n,k,a):
    arr = []
    locmax = 0
    for i in a:
        arr.append(locmax)
        locmax = max(locmax,i)

    ans = 2**60
    for c in combinations(range(1,n),k-1):
        cost = 0
        prev = a[0]
        for i in c:
            if a[i]<=prev:
                cost += max(prev,arr[i])+1-a[i]
            prev = max(max(prev,arr[i])+1,a[i])
        ans = min(ans,cost)
    if k==1:
        ans = 0
    print(ans)

if __name__=="__main__":
    n,k,a = getval()
    main(n,k,a)   