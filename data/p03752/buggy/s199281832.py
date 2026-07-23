n, k = map(int, input().split())
li = list(map(int, input().split()))
min_ = 10**12
for i in range(1<<n):
    max_height = li[0]
    money = 0
    can_look = 0
    li_h = []
    for j in range(n):
        if j != 0:
            max_height = max(max_height, li_h[j-1])
        
        if j == 0:
            can_look += 1
            li_h.append(li[0])
            continue
        if (i>>j)&1:
            can_look += 1
            if li[j] <= max_height:
                li_h.append(max_height+1)
            else:
                li_h.append(li[j])
        else:
            li_h.append(li[j])
    if can_look >= k:
        money = sum(li_h) - sum(li)
        min_ = min(min_, money)
        print(li_h)
        print(li)
        
print(min_)