S = input()
a = []
r_ = 0 
l_ = 0
flag = 0
for i in range(len(S)):
    if flag == 0:
        if S[i]=="R":
            r_ = r_ +1
            continue
        elif i != len(S) -1:
            flag = 1
            l_ = l_ +1
            continue
        else:
            l_ = l_ +1
            al = l_ + r_
            a.append([al,r_])
            continue
            
    if flag == 1:
        if S[i] == "L"   :
            l_ = l_ +1
        else:
            al = l_ + r_
            a.append([al,r_])
            r_ = 1
            l_ = 0 
            flag = 0
        if i == len(S) -1:
            al = l_ + r_
            a.append([al,r_])
 

ans = []
for i in range(len(a)):
    n = a[i][0]
    r = a[i][1]
    odd = n 
    eve = n - odd
    for j in range(r -1):
        ans.append(0)
    if r 
        ans.append(eve)
        ans.append(odd)
    else:
        ans.append(odd)
        ans.append(eve)
    for j in range(n -r -1):
        ans.append(0)
print(*ans)
    
            

    