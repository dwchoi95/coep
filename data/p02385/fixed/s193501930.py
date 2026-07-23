dice_1 = input().split()
dice_2 = input().split()

rolls = {' ':[0, 1, 2, 3, 4, 5], 
         'W':[2, 1, 5, 0, 4, 3], 
         'N':[1, 5, 2, 3, 0, 4], 
         'E':[3, 1, 0, 5, 4, 2], 
         'S':[4, 0, 2, 3, 5, 1]
        }
orders = [' ', 'N', 'W', 'E', 'S', 'NN']
tf = 0
for order in orders:
    copy_2 = dice_2
    for d in order:
        roll = rolls[d]
        copy_2 = [copy_2[i] for i in roll]
    
    l = [1, 2, 4, 3]
    a0 = copy_2[0] == dice_1[0]
    a1 = copy_2[5] == dice_1[5]
    a2 = ' '.join([copy_2[s]for s in l]) in ' '.join([dice_1[s]for s in l] * 2)
    if  a0 and a1 and a2:
        tf += 1






if tf>0:
    print('Yes')
else:
    print('No')
