


n,m = map(int,input().split())

lis = [0] * m

state = [0] * n

a = list(map(int,input().split()))

start = [ [] for i in range(m) ]
end = [ [] for i in range(m)]

allsum = 0
for i in range(n-1):

    if a[i+1] == a[i]+1:
        continue

    start[a[i] % m].append(i)
    end[(a[i+1]-1) % m].append(i)

    allsum += (a[i+1]-a[i]) % m


imosnum = 0
plus = 0



for i in range(2*m):

    plus += imosnum

    lis[i%m] += plus

    for j in end[i%m]:
        if state[j] == 1:
            plus -= ((a[j+1]-(a[j]+1))%m)
            state[j] = 2
            imosnum -= 1

    for j in start[i%m]:
        if state[j] == 0:
            imosnum += 1
            state[j] = 1

    

print (allsum - max(lis))