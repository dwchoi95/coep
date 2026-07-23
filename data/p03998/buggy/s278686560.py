SA = list(str(input())) 
SB = list(str(input())) 
SC = list(str(input())) 
card = 'a'

for i in range(301):
    if len(SA)==1 and card =='a':
        print('A')
        break
    elif len(SB)==1 and card=='b':
        print('B')
        break
    elif len(SC)==1 and card=='c':
        print('C')
        break
        
    if card == 'a':
        SA = SA[1:]
        card = SA[0]
    elif card == 'b':
        SB = SB[1:]
        card = SB[0]
    elif card == 'c':
        SC =SC[1:]
        card = SC[0]