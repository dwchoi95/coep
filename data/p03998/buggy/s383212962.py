a = input()
b = input()
c = input()

cards = {'a': a, 'b': b, 'c': c}
turn = 'a'

while True:
    if len(cards[turn]) == 0:
        print(turn)
        break
    draw = cards[turn][0]
    cards[turn] = cards[turn][1:]
    turn = draw
