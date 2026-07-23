import math

n = int(input())
N = n

if(n == 1):
    print(0)
    exit()

yakusu = []
multi = []

i = 2
while(i <= math.ceil(math.sqrt(n))):
    
    if(n % i == 0):
        if(i in yakusu):
            multi[yakusu.index(i)] += 1
        else:
            yakusu.append(i)
            multi.append(1)
        n = int(n / i)
        continue
    
    if(n == 1):
        break
    
    i += 1

if(len(yakusu) == 0):
    print(1)
    exit()
    
ans = 0

for j in range(len(multi)):
    h = (-1 + int(math.sqrt(1 + 8 * multi[j]))) / 2
    ans += int(h)

print(ans)