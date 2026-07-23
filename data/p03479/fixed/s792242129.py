X,Y=list(map(int, input().split()))
present=[X]
i=0
while present[i]<=Y:
    present.append(present[i]*2)
    i=i+1

print(len(present)-1)