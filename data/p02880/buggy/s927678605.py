dic={}

for i in range(9):
    for j in range(9):
        if dic.get(i*j,None)==None:
            dic[i*j]=1
        else:
            dic[i*j]+=1

N = int(input())

if dic.get(N,None)==None:
    print("No")
else:
    print("Yes")