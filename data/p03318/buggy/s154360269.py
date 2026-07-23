

K = int(input())


Sunuke = [1, 2, 3, 4, 5, 6, 7, 8]


if K <= len(Sunuke):
    for i in range(K):
        print(Sunuke[i])

else:
    
    resi = K - len(Sunuke)
    
    digit = 1

    while resi > 0:
        
        for i in range(1, 10):
            num = i * (10**digit) - 1
            Sunuke.append(num)

            resi -= 1
            
            

        digit += 1


for i in range(K):
    print(Sunuke[i])