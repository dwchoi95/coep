class Dice():
    def __init__(self,ary):
        self.top = ary[0]
        self.south = ary[1]
        self.east = ary[2]
        self.west = ary[3]
        self.north = ary[4]
        self.bottom = ary[5]

    def get_top(self):
        return self.top

    def rotate_north(self):
        self.top,self.south,self.north,self.bottom = self.south,self.bottom,self.top,self.north
    
    def rotate_south(self):
        self.top,self.south,self.north,self.bottom = self.north,self.top,self.bottom,self.south

    def rotate_west(self):
        self.top,self.west,self.bottom,self.east = self.east,self.top,self.west,self.bottom

    def rotate_east(self):
        self.top,self.west,self.bottom,self.east = self.west,self.bottom,self.east,self.top

    def rotate_horizon(self):
        self.south,self.east,self.north,self.west = self.west,self.south,self.east,self.north

    def get_east(self):
        return self.east
        
dice1 = Dice(list(map(int,input().split())))
dice2 = Dice(list(map(int,input().split())))

h=""

for i in range(4):
    dice2.rotate_west()
    if dice1.top == dice2.top:
        for _ in range(4):
            dice2.rotate_horizon()
            if dice1.south == dice2.south:
                if dice1.east == dice2.east:
                    h = "Yes"
for _ in range(4):
    dice2.rotate_north()
    if dice1.top == dice2.top:
        for m in range(4):
            dice2.rotate_horizon()
            if dice1.south == dice2.south:
                if dice1.east == dice2.east:
                    h = "Yes"
if h:
    print(h)
else:
    print("No")