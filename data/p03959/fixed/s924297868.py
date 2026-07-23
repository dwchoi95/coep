import sys
input = sys.stdin.buffer.readline
from operator import itemgetter

def main():
    N = int(input())
    
    t = list(map(int,input().split()))
    a = list(map(int,input().split()))
    MOD = 10**9+7
    
    tt,tl = 0,[False for _ in range(N)]
    for x,num in enumerate(t):
        if num > tt:
            tl[x] = True
            tt = num
            
    at,al = 0,[False for _ in range(N)]
    for x,num in enumerate(a[::-1]):
        if num > at:
            al[-x-1] = True
            at = num

    ans,now = 1,0
    for i in range(N):
        if tl[i] == True and al[i] == True:
            if now < t[i] == a[i]:
                now = a[i]
            else:
                print(0)
                exit()
        elif tl[i] == True and al[i] == False:
            if t[i] > a[i]:
                print(0)
                exit()
            else:
                now = t[i]
        elif tl[i] == False and al[i] == True:
            if t[i] < a[i]:
                print(0)
                exit()
            else:
                now = a[i]
        else:
            ans *= min(t[i],a[i])
            ans %= MOD
    
    print(ans)

if __name__ == "__main__":
    main()
