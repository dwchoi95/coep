S = input()
counter = 0




















sum=0
for i in range(len(S)):
    if S[i]=='W':
        sum+=i
        counter+=1
print(sum-counter)