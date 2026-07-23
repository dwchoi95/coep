turn = "a"
S = {}
S["a"] = list(input())
S["b"] = list(input())
S["c"] = list(input())

while True:
    nextturn = S[turn].pop(0)
    if len(S[turn]) == 0:
        print(turn.upper())
        break
    else:
        turn = nextturn
        