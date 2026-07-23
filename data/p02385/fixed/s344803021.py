


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
        elif ope == 'R': 
            self.south, self.east, self.north, self.west = self.east, self.north, self.west, self.south
        elif ope == 'L': 
            self.south, self.east, self.north, self.west = self.west, self.north, self.east, self.south
        else:
            pass

    def get_surfaces(self):
        return [self.top, self.south, self.east, self.north, self.west, self.bottom]

dc1 = dice([int(x) for x in input().split(' ')])
dc2 = dice([int(x) for x in input().split(' ')])

judged = False
if len((dc1.get_surfaces() and dc2.get_surfaces())) == 6:
    opes = ['', 'S', 'E', 'S', 'E', 'S']
    for op in opes:
        dc2.rotate(op)
        for i in range(4):
            if dc1.get_surfaces() == dc2.get_surfaces():
                judged = True
                break
            dc2.rotate('R')
        if judged: break

if judged:
    print('Yes')
else:
    print('No')
