n,m = map(int,input().split())
drink = dict()
cost = set()
ans = 0
for i in range(n):
    ab = [int(i) for i in input().split()]
    cost.add(ab[0])
    if ab[0] in drink:
        drink[ab[0]] += ab[1]
    else:
        drink[ab[0]] = ab[1]

sorted(cost)
for i in cost:
    if m <= drink[i]:
        ans += m*i
        break
    else:
        m -= drink[i]
        ans += i * drink[i] 
    
print(ans)