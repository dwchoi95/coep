N = int(input())
N_prime = []

n = N
i = 2
while i <= N**0.5:
    if n%i != 0:
        i += 1
        continue
    
    N_prime.append(i)
    n = n/i
    if n == 1:
        break

if N_prime == []:
    N_prime.append(N)
elif n != 1:
    N_prime.append(int(n))

ct = []
for i in N_prime:
    if i not in ct:
        ct.append(i)
        temp_i = 1
        continue
    temp_i *= i
    if temp_i not in ct:
        ct.append(temp_i)
        temp_i = i
        continue

print(len(ct))