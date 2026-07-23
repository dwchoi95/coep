mod=10**9+7
n,m=map(int,input().split())
x=list(map(int,input().split()))
y=list(map(int,input().split()))
ansx=0
cum=x[0]
for i in range(1,n):
    ansx+=(i*x[i]-cum+mod)%mod
    ansx%=mod
    cum+=x[i]
ansy=0
cum=y[0]
for i in range(1,m):
    ansy+=(i*y[i]-cum+mod)%mod
    ansy%=mod
    cum+=y[i]
print(ansx,ansy)
print((ansx*ansy)%mod)
