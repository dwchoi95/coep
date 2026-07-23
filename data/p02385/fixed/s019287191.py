


class Dice:
    def __init__(self, ary):
        self.top, self.south, self.east, self.west, self.north, self.bottom = ary

    def roll_n(self):
        self.top, self.north, self.bottom, self.south = self.south, self.top, self.north, self.bottom

    def roll_e(self):
        self.top, self.east, self.bottom, self.west = self.west, self.top, self.east, self.bottom

    def twist(self):
        self.north, self.east, self.south, self.west = self.west, self.north, self.east, self.south

    def isEqual(self, dice):
        if self.top == dice.top and self.south == dice.south and self.east == dice.east and self.west == dice.west and self.north == dice.north and self.bottom == dice.bottom:
            return True
        else:
            return False

dice1 = Dice(map(int,input().split()))
dice2 = Dice(map(int,input().split()))

flag = False

for i in range(6):
    if i % 2 == 0:
        dice1.roll_n()
    else:
        dice1.roll_e()

    for j in range(4):
        if dice1.isEqual(dice2):
            flag = True
            break
        else:
            dice1.twist()

    if flag:
        break

if flag:
    print('Yes')
else:
    print('No')