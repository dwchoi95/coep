

K = int(input())

Sunuke = [1, 2, 3, 4, 5, 6, 7, 8, 9]

def ns(n):
    return n / sum(map(int, list((str(n)))))


if K <= len(Sunuke):
    for i in range(K):
        print(Sunuke[i])

else:
    
    resi = K - len(Sunuke)
    
    digit = 0
    snk = 9

    while resi > 0:
        nxt1 = snk + 10**digit
        nxt2 = snk + 10**(digit+1)

        
        if ns(nxt1) > ns(nxt2):
            digit +=1
            snk = nxt2
            Sunuke.append(snk)
            resi -= 1
        else:
            snk = nxt1
            Sunuke.append(snk)
            resi -= 1


for i in range(K):
    print(Sunuke[i])