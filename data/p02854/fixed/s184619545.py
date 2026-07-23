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
for ii,ss in enumerate(sum_li):
    if ii == len(sum_li)-1:
        break
    all_li.append(abs(s-2*ss))

print(min(all_li))