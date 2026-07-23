n,m = map(int,input().split())
drink = dict()
cost = list()
ans = 0
for i in range(n):
    ab = [int(i) for i in input().split()]
    if ab[0] in drink:
        drink[ab[0]] += ab[1]
    else:
        cost.append(ab[0])
        drink[ab[0]] = ab[1]

cost.sort()
for i in cost:
    if m <= drink[i]:
        ans += m*i
        break
    else:
        m -= drink[i]
        ans += i * drink[i] 
    
print(ans)