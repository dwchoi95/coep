

k = int(input())
k = 100
count = 0
ans = []
minN = 10**15

for i in reversed(range(5)):
    for j in reversed(range(1,10**4)):
        num = str(j)+"9"*i*3
        n = sum([int(k) for k in num])
        n = int(num)/n
        if(num == "379999"):
            print("tes")
        if(minN > n or n==1):
            minN = n
            ans.append(num)

print(len(ans[0]),len(ans))

for i in list(reversed(ans))[:k]:
    print(i)