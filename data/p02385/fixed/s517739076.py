import sys
class Dice:
    def __init__(self, f):
        self.f = f[:]

    def roll(self, s):
        for f in s:
            n = self.f[:]
            if f == 'E':
                t = n[0]
                n[0] = n[3]
                n[3] = n[5]
                n[5] = n[2]
                n[2] = t
            elif f == 'W':
                t = n[0]
                n[0] = n[2]
                n[2] = n[5]
                n[5] = n[3]
                n[3] = t
            elif f == 'N':
                t = n[0]
                n[0] = n[1]
                n[1] = n[5]
                n[5] = n[4]
                n[4] = t
            else:
                t = n[0]
                n[0] = n[4]
                n[4] = n[5]
                n[5] = n[1]
                n[1] = t
            self.f = n

    def to_top(self, index):
        if index == 1:
            self.roll('N')
        elif index == 2:
            self.roll('W')
        elif index == 3:
            self.roll('E')
        elif index == 4:
            self.roll('S')
        elif index == 5:
            self.roll('NN')
        return self

    def side_roll(self):
        t  = self.f[1]
        self.f[1] = self.f[2]
        self.f[2] = self.f[4]
        self.f[4] = self.f[3]
        self.f[3] = t
        return self

    def all_face(self):
        faces = []
        for i in range(0,6):
            t = Dice(self.f[:])
            faces.append(t.to_top(i).f[:])
            for j in range(3):
                faces.append(t.side_roll().f[:])
        return faces

d1, d2 = (Dice(list(input().split())) for _ in range(2))
fs = d1.all_face()
print('Yes' if d2.f in fs else 'No')