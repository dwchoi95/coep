n = int(input())
li = list(map(int,input().split()))
s = sum(li)
sum_li = []
for i,l in enumerate(li):
    if i == 0:
        sum_li.append(l)
        continue
    sum_li.append(sum_li[-1]+l)
all_li = []
for ss in sum_li:
    
    all_li.append(abs(s-ss))
print(min(all_li))
