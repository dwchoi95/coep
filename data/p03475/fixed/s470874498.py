N = int(input())-1
timeLine = [[0 for x in range(3)] for y in range(N)]
for i in range(N):
    tmp = input().split()
    timeLine[i][0],timeLine[i][1],timeLine[i][2] = int(tmp[0]),int(tmp[1]),int(tmp[2])
for j in range(N):
    total = timeLine[j][0] + timeLine[j][1]
    now = j+1
    while now <= (N-1):
        if timeLine[now][1] >= total:
            total = timeLine[now][1] + timeLine[now][0]
        else:
            if timeLine[now][1] + timeLine[now][2] >= total:
                total = timeLine[now][0] + timeLine[now][1] + timeLine[now][2]
            else:
                n = int((total-timeLine[now][1])/timeLine[now][2])
                if (total-timeLine[now][1]) % timeLine[now][2] > 0:
                    n += 1
                total = timeLine[now][0] + timeLine[now][1] + timeLine[now][2] * n
        now +=1
    print(total)
print(0)