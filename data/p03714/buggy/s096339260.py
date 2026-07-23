import sys
input = sys.stdin.readline

def I(): return int(input())
def MI(): return map(int, input().split())
def LI(): return list(map(int, input().split()))
import heapq

def main():
    mod=10**9+7
    N=I()
    a=LI()
    q1=a[:N]
    s1=[0]*(N+1)
    s1[0]=sum(q1)
    heapq.heapify(q1)
        
    q2=[]
    heapq.heapify(q2)
    s2=[0]*(N+1)
    for i in range(N):
        b=a[-1-i]*(-1)
        s2[0]+=b
        heapq.heappush(q2,b)
    
    
    for i in range(N):
        b=heapq.heappop(q1)
        s1[i+1]=s1[i]+a[i+N]-b
        
        c=heapq.heappop(q2)
        s2[i+1]=s2[i]+a[-1-N-i]*(-1)-c
        
    L=[0]*(N+1)
    ans=-1*10**16
    for i in range(N+1):
        temp=s1[i]+s2[-1-i]
        if ans<temp:
            ans=temp
    print(ans)
        
        
    

main()
