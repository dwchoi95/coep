a = input()
b = input()
c = input()
countlist = [1, 0, 0]
list = ["a", "b", "c"]
turn = 0
value = ""
for x in range(len(a) + len(b) + len(c)):
    
    if countlist[0] > len(a) or countlist[1] > len(b) or countlist[2] > len(c): break
    if turn == 0: value = a[countlist[turn] - 1]
    elif turn == 1: value = b[countlist[turn] - 1]
    elif turn == 2: value = c[countlist[turn] - 1]
        
    turn = list.index(value)
    countlist[turn] += 1
    print(countlist)

if countlist[0] > len(a): print("A")
elif countlist[1] > len(b): print("B")
elif countlist[2] > len(c): print("C")
