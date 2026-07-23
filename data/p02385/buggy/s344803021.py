


class dice():
    def __init__(self, arr):
        self.top = arr[0]
        self.south = arr[1]
        self.east = arr[2]
        self.west = arr[3]
        self.north = arr[4]
        self.bottom = arr[5]

    def rotate(self, ope):
        if ope == 'S':
            self.top, self.north, self.bottom, self.south = self.north, self.bottom, self.south, self.top
        elif ope == 'N':
            self.top, self.south, self.bottom, self.north = self.south, self.bottom, self.north, self.top
        elif ope == 'E':
            self.top, self.west, self.bottom, self.east = self.west, self.bottom, self.east, self.top
        elif ope == 'W':
            self.top, self.east, self.bottom, self.west = self.east, self.bottom, self.west, self.top

    def get_surfaces(self):
        return [self.top, self.south, self.east, self.north, self.west, self.bottom]

dc1 = dice([int(x) for x in input().split(' ')])
dc2 = dice([int(x) for x in input().split(' ')])

judged = False
if len((dc1.get_surfaces() and dc2.get_surfaces())) == 6:
    if dc2.top != dc1.top:
        opes = ['S', 'E', 'S', 'E', 'S']
        for op in opes:
            dc2.rotate(op)
            if dc2.top == dc1.top: break
    for i in range(4):
        if dc2.south == dc1.south:
            break
        dc2.rotate('R')
    if (dc1.east == dc2.east) and (dc1.north == dc2.north) and (dc1.bottom == dc2.bottom):
        judged = True

if judged:
    print('Yes')
else:
    print('No')
