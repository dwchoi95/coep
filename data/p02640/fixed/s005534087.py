
X,Y = map(int,input().split())

turu = 2
kame = 4
flag = False
for i in range(0, X + 1): 
    
    turu_num = X - i
    
    leg_total = kame * i + turu_num * turu
    
    if(leg_total == Y):
      flag = True
      break




if flag:
    print("Yes")
else:
    print("No")