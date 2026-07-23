a = input()
b = input()
c = input()



next = 'a'

while True:

    if not a:
        print('A')
        exit()
    if not b:
        print('B')
        exit()
    if not c:
        print('C')
        exit()

    if next == 'a':
        next = a[-1]
        a = a[:-1]

    elif next == 'b':
        next = b[-1]
        b = b[:-1]
    else:
        next = c[-1]
        c = c[:-1]
