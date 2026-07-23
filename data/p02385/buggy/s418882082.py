


class Dice:
    def __init__(self, n):
        self.upper    = n[0]
        self.backward = n[1]
        self.right    = n[2]
        self.left     = n[3]
        self.ahead    = n[4]
        self.bottom   = n[5]

    def roll_north(self):
        self.upper, self.ahead, self.bottom, self.backward = self.backward, self.upper, self.ahead, self.bottom

    def roll_south(self):
        self.upper, self.ahead, self.bottom, self.backward = self.ahead, self.bottom, self.backward, self.upper

    def roll_east(self):
        self.upper, self.right, self.bottom, self.left = self.left, self.upper, self.right, self.bottom

    def roll_west(self):
        self.upper, self.right, self.bottom, self.left = self.right, self.bottom, self.left, self.upper

    def roll_side(self):
        self.ahead, self.right, self.backward, self.left = self.left, self.ahead, self.right, self.backward


def match_dice(dice1, dice2):
    for i in range(4):
        dice1.roll_north()

        for j in range(4):
            dice1.roll_east()

            for k in range(4):
                dice1.roll_side()

                if dice1 is dice2:
                    return 0
    return 1


dice1 = Dice(list(map(int, input().split())))
dice2 = Dice(list(map(int, input().split())))
result = match_dice(dice1, dice2)

if result is 0:
    print('Yes')
else:
    print('No')
    
