S = input()
counter = 0




















sum=0
for i in range(len(S)):
    if S[i]=='W':
        sum+=i
        counter+=1

n=counter-1
minus=n*(n+1)/2
print(int(sum-minus))