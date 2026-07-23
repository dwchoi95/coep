s=input()
n=len(s)
res=0
tg,tp=0,0
for i in range(n):
    if s[i]=="g":
        if tg>tp:
            tp+=1
            res+=1
        else:
            tg+=1
    else:
        if tg<=tp:
            tp+=1
        else:
            tg+=1
            res-=1
print(res)