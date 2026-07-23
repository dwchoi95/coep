x,y,a,b,c = map(int,input().split())
p_ = list(map(int,input().split()))
q_ = list(map(int,input().split()))
r_ = list(map(int,input().split()))
p_.sort(reverse=True)
q_.sort(reverse=True)
r_.sort(reverse=True)
red = x-1
gre = y-1
mu = 0
while True:
    if mu == c:
        break
    else:
        if red >= 0:
            badr = p_[red]
        else:
            badr = 1000000000
        if gre >= 0:
            badg = q_[gre]
        else:
            badg = 1000000000
        badmu = r_[mu]
        if badr <= badg:
            if badr < badmu:
                red = red-1
                mu = mu+1
            else:
                break
        else:
            if badg < badmu:
                gre = gre-1
                mu = mu+1
            else:
                break
ans = 0
for i in range(red+1):
    ans += p_[i]
for i in range(gre+1):
    ans += q_[i]
for i in range(mu):
    ans += r_[i]
print(ans)