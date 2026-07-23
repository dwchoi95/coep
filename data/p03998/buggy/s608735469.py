a,b,c=input(),input(),input()
string=[a,b,c]
s=[0,0,0]
ban=0
print(string)
while s[0]!=len(a) and s[1]!=len(b) and s[2]!=len(c):
    temp=s[ban]
    s[ban]+=1
    if string[ban][temp]=="a": ban=0
    elif string[ban][temp]=="b": ban=1
    else: ban=2

if s[0]==len(a): print("A")
if s[1]==len(b): print("B")
if s[2]==len(c): print("C")