def f(n):
    s=str(n)
    return sum([int(s[i]) for i in range(len(s))])

sunuke=[]
for i in range(100):
    for j in range(2,11):
        sunuke.append(j*(10**i)-1)
L=len(sunuke)
tmp=sunuke[L-1]/f(sunuke[L-1])
ans=[sunuke[L-1]]
for i in range(len(sunuke)-2,-1,-1):
    x=sunuke[i]/f(sunuke[i])
    if x<=tmp:
        ans.append(sunuke[i])
        tmp=x
ans=ans[::-1]

    

for i in range(int(input())):
    print(ans[i])
