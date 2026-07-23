def N():
    num=Dice[0]
    Dice[0]=Dice[1]
    Dice[1]=Dice[5]
    Dice[5]=Dice[4]
    Dice[4]=num
def E():
    num=Dice[0]
    Dice[0]=Dice[3]
    Dice[3]=Dice[5]
    Dice[5]=Dice[2]
    Dice[2]=num
def W():
    num=Dice[0]
    Dice[0]=Dice[2]
    Dice[2]=Dice[5]
    Dice[5]=Dice[3]
    Dice[3]=num
def S():
    num=Dice[0]
    Dice[0]=Dice[4]
    Dice[4]=Dice[5]
    Dice[5]=Dice[1]
    Dice[1]=num
Dice=[int(i) for i in input().split()]
Dice2=[int(i) for i in input().split()]
if (Dice[0] in Dice2)==False:
    print('No')
else:
    for j in range(6):
        if j%2==0:
            N()
        else:
            W()
        for i in range(4):
            N()
            W()
            S()
            if Dice==Dice2:
                break
        if Dice==Dice2:
            break 
    if Dice==Dice2:
        print('Yes')
    else:
        print('No')