N = int(input())
l = [list(map(int, input().split())) for j in range(N-1)]

t = []
for i in range(N-1):
    t.append(l[i][0]+l[i][1])
    for j in range(1, N-i-1):
        if t[i] < l[i+j][1]:
            t[i] = l[i+j][1] + l[i+j][0]
           
        else: 
            t[i] += -(t[i]%(l[i+j][2])) + l[i+j][2] + l[i+j][0] 

t.append(0)
for i in range(N):
    print(t[i])

