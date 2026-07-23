n = int(input())
p = 1
mod  = int(10e9+7)
for i in range(1,n+1):
    p *=i
    p = p%mod
print(p)