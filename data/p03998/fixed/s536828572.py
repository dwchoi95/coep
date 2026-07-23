turn = "a"
S = {}
S["a"] = list(input())
S["b"] = list(input())
S["c"] = list(input())

while True:
    turn = S[turn].pop(0)
    if len(S[turn]) == 0:
        print(turn.upper())
        break