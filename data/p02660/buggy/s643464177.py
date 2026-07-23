import math


def is_prime(n):
    for i in range(2, int(math.sqrt(n))+1):
        if n%i == 0:
            return False
    return True

def getPrimeExp(n):
    n_sqrt = int(math.sqrt(n))
    array = [True]*(n_sqrt+1)
    result = []
    for i in range(2, n_sqrt+1):
        if array[i]:
            array[i] = False
            result.append(i)
            for j in range(2, n_sqrt+1):
                ij = i**j
                if ij <= n_sqrt and array[ij]:
                    result.append(ij)
                    array[ij] = False
                elif ij > n:
                    break
            for j in range(i*2, n_sqrt+1, i):
                array[j] = False

            
            
            
            
            
    return sorted(result)

N = int(input())
if N == 1:
    print(0)
elif is_prime(N) and N != 1:
    print(1)
else:
    cnt = 0
    primeExp = getPrimeExp(N) 
    n = N
    
    for z in primeExp:
        if n%z == 0:
            n = int(n/z)
            cnt += 1
    print(cnt)