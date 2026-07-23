SA, SB, SC = [input() for i in range(3)]
SA = SA + '0'
SB = SB + '0'
SC = SC + '0'

card = SA[0]
SA = SA[1:]

for i in range(303):
    if SA == '0' and card == 'a':
        print('A')
        break
    elif SB == '0' and card == 'b':
        print('B')
        break
    elif SC == '0' and card == 'c':
        print('C')
        break
    
    if card == 'a':
        card = SA[0]
        SA = SA[1:]
    elif card == 'b':
        card = SB[0]
        SB = SB[1:]
    elif card == 'c':
        card = SC[0]
        SC = SC[1:]