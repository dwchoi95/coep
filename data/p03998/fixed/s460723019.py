
from collections import deque
S_A = deque(input())
S_B = deque(input())
S_C = deque(input())


next_turn = 'a'

while True:
    
    if len(S_A) == 0 and next_turn == 'a':
        print("A")
        exit()
    elif len(S_B) == 0 and next_turn == 'b':
        print("B")
        exit()
    elif len(S_C) == 0 and next_turn == 'c':
        print("C")
        exit()
    else:
        if next_turn == 'a':
            next_turn = S_A.popleft()
        elif next_turn == 'b':
            next_turn = S_B.popleft()
        elif next_turn == 'c':
            next_turn = S_C.popleft()
