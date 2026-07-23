n = int(input())
a = list(map(int, input().split()))
b = list(map(int, input().split()))
b.append(0)

sum = 0
rest_hero = 0

for i in range(n+1):
    hero = b[i] + rest_hero
    if a[i] >= hero:
        sum += hero
        rest_hero = 0
    else:  
        sum += a[i]
        if a[i] > rest_hero:
            rest_hero = b[i] - (a[i] - rest_hero)
        else:
            rest_hero = b[i]

print(sum)
