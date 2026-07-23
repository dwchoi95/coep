class Dice:

    def __init__(self):
        
        
        self.t = 1
        self.s = 2
        self.e = 3
        self.w = 4
        self.n = 5
        self.b = 6
        self.rotway = {"S": 0, "N": 1, "E": 2, "W": 3}

    def __init__(self, t, s, e, w, n, b):
        
        self.t = t
        self.s = s
        self.e = e
        self.w = w
        self.n = n
        self.b = b
        self.rotway = {"S": 0, "N": 1, "E": 2, "W": 3}

    def rot(self, way):
        if way == 0:
            self.t, self.s, self.e, self.w, self.n, self.b = self.n, self.t, self.e, self.w, self.b, self.s
        elif way == 1:
            self.t, self.s, self.e, self.w, self.n, self.b = self.s, self.b, self.e, self.w, self.t, self.n
        elif way == 2:
            self.t, self.s, self.e, self.w, self.n, self.b = self.w, self.s, self.t, self.b, self.n, self.e
        elif way == 3:
            self.t, self.s, self.e, self.w, self.n, self.b = self.e, self.s, self.b, self.t, self.n, self.w
        
        
def main():
    import random

    t1,s1,e1,w1,n1,b1 = map(int, input().split())
    t2,s2,e2,w2,n2,b2 = map(int, input().split())

    dice1 = Dice(t1,s1,e1,w1,n1,b1)
    dice2 = Dice(t2,s2,e2,w2,n2,b2)

    flag = 0

    for _ in range(10000):

        if (dice1.t, dice1.s, dice1.e, dice1.w, dice1.n, dice1.b) == (dice2.t, dice2.s, dice2.e, dice2.w, dice2.n, dice2.b):
            flag = 1
            break
        else:
            seed = random.randint(0, 3)
            dice2.rot(seed)

    if flag == 1:
        print("Yes")
    else:
        print("No")



if __name__ == '__main__':
    main()

