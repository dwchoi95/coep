m=float("INF")
sunukes=[]
for i in range(15,-1,-1):
    for j in range(100,10,-1):
        
        sunuke=j*(10**i)-1
        s=str(sunuke)
        sn=0
        for k in range(len(s)):
            sn+=int(s[k])
        x=sunuke/sn
        
        if x<=m :
            m=x
            sunukes.append(sunuke)
for i in range(9,0,-1):
    sunukes.append(i)
k=int(input())

print(sunukes[-k])
