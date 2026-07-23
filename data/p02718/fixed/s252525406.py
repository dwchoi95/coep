(N, M) = [int(x) for x in input().split()]
line=[int(x) for x in input().split()]
cutoff=sum(line)/(4*M)
count=N
for i in line:
    if i<cutoff:
        count-=1
if count>=M:
    print("Yes")
else:
    print("No")
