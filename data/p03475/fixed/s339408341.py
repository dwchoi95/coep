import sys,math
input = sys.stdin.readline

N = int(input())
CSF = [[0,0,0]]
for i in range(1,N):
    CSF.append(list(map(int,input().split())))
for i in range(1,N+1):
    nowtime = 0
    for j in range(i,N):
        if nowtime <=CSF[j][1]:
            depT =CSF[j][1]
        else:
            depT =CSF[j][1] + math.ceil((nowtime-CSF[j][1])/CSF[j][2])*CSF[j][2]

        nowtime = depT+CSF[j][0]
        
    print(nowtime)