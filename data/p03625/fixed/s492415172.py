from collections import Counter
n=int(input())
a=sorted([int(i) for i in input().split()])
cnt=Counter(a)
key=sorted(list(cnt.keys()))[::-1]
one=two=0
for i in key:
    if cnt[i]>=4 and one==0:
        one=two=i
        break
    elif cnt[i]>=2:
        if one==0:
            one=i
        else:
            two=i
            break
print(one*two)