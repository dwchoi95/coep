def main():
    H, W, N = map(int, input().split())
    sr, sc = map(int, input().split())
    S = input()
    T = input()
    S = S[::-1]
    T = T[::-1]
    L, R, U, D = 1, W, 1, H
    f = False
    if S[0] == "L":
        L += 1
    elif S[0] == "R":
        R -= 1
    elif S[0] == "U":
        U += 1
    else:
        D -= 1
    if R < L or D < U:
        f = True
    for i in range(1, N):
        if (S[i] == "L" and T[i] == "R") or (S[i] == "R" and T[i] == "L") or (S[i] == "U" and T[i] == "D") or (S[i] == "D" and T[i] == "U"):
            continue
        if S[i] == "L":
            L += 1
        elif S[i] == "R":
            R -= 1
        elif S[i] == "U":
            U += 1
        else:
            D -= 1
        if R < L or D < U:
            f = True
    if sr < U or D < sr or sc < L or R < sc:
        f = True
    if f:
        print("NO")
    else:
        print("YES")

if __name__ == "__main__":
    main()
