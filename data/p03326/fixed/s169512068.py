N,M=map(int,input().split())
xyz=[list(map(int,input().split())) for i in range(N)]
MAX=0
for index in [[1,1,1],[1,1,-1],[1,-1,1],[1,-1,-1],[-1,1,1],[-1,1,-1],[-1,-1,1],[-1,-1,-1]]:
    LIST=sorted([sum([p[a]*index[a] for a in range(3)]) for p in xyz])[::-1]
    if sum(LIST[0:M])>MAX:
        MAX=sum(LIST[0:M])
print(MAX)