N = int(input())
CSF = [list(map(int,input().split())) for i in range(N-1)]
CSF.append([0,0,1])
ans=[0]*N 
for i in range(N-1):
    for j in range(i,N-1):
        if j == i:
            ans[i]+=CSF[j][0]+CSF[j][1]
        else:
            if ans[i]<=CSF[j][1]:
                ans[i]=CSF[j][0]+CSF[j][1]
            elif (ans[i]-CSF[j][1])%CSF[j][2]==0:
                ans[i]+=CSF[j][0]
            else:
                ans[i]+=(CSF[j][2]-(ans[i]-CSF[j][1])%CSF[j][2])+CSF[j][0] 
for i in range(N):
    print(ans[i])