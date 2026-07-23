num = []
vote = []
num = list(map(int,input().split()))
vote = list(map(int,input().split()))
N = num[0]
M = num[1]
j = sum(vote)/(4*M)


cnt = 0
for i in vote:
    if  i>=j:
        cnt += 1
    else:
        pass

if M<=cnt:
    print("Yes")
else:
    print("No")
