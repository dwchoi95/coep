a,b,c=input(),input(),input()
string=[a,b,c]
ans=["A","B","C"]
s=[0,0,0]
ban=0
while s[ban]!=len(string[ban]):
    temp=s[ban]
    s[ban]+=1
    if string[ban][temp]=="a": ban=0
    elif string[ban][temp]=="b": ban=1
    else: ban=2
print(ans[ban])