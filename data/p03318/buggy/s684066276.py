

K = int(input())

Sunuke = [1, 2, 3, 4, 5, 6, 7, 8, 9]


if K <= len(Sunuke):
    for i in range(K):
        print(Sunuke[i])

else:
    resi = K - len(Sunuke)
    digit = 1
    num = 19
    Sunuke.append(num)
    resi -= 1
    endFlg = False
    while resi > 0:
        for d in range(1, digit+1):
            for i in range(9):
                num += 10
                Sunuke.append(num)

                resi -= 1
                if resi == 0:
                    endFlg = True
                    break
            if endFlg:
                break

for i in range(K):
    print(Sunuke[i])