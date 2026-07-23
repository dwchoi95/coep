N = int(input())
l = list(map(int, input().split()))

mean = round(sum(l)/N)
stamina = 0

for p in l:
    stamina += (p - mean)**2

print(stamina)