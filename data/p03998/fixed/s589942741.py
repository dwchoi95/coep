a = input()
b = input()
c = input()


turn = 'a'

A = B = C = 0

while 1:

    if turn == 'a':
        if len(a) == A:
            print('A')
            break
        turn = a[A]
        A+=1

    elif turn == 'b':
        if len(b) == B:
            print('B')
            break
        turn = b[B]
        B+=1
    else:
        if len(c) == C:
            print('C')
            break
        turn = c[C]
        C+=1
