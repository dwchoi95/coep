

k = int(input())

count = 0
ans = []
minN = 10**15

for i in reversed(range(15)):
    for j in reversed(range(1,100)):
        num = str(j)+"9"*i
        n = sum([int(k) for k in num])
        n = int(num)/n
        if(minN > n):
            minN = n
            ans.append(num)
            
for i in list(reversed(ans))[:k]:
    print(i)