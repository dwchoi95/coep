N = int(input())
l = map(int, input().split())

mean = int(sum(l)/N)

stamina = 0

for p in l:
	stamina += (p - mean)**2
    
print(stamina)