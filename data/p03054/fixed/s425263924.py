def main():
    H, W, N = map(int, input().split())
    sr, sc = map(int, input().split())
    S = input()
    T = input()
    f = True
    pL, pR, pU, pD = sc, sc, sr, sr
    for i in range(N):
        if S[i] == "L":
            pL -= 1
        elif S[i] == "R":
            pR += 1
        elif S[i] == "U":
            pU -= 1
        else:
            pD += 1
        if pL <= 0 or W < pR or pU <= 0 or H < pD:
            f = False
        if T[i] == "L":
            if 1 < pR:
                pR -= 1
        elif T[i] == "R":
            if pL < W:
                pL += 1
        elif T[i] == "U":
            if 1 < pD:
                pD -= 1
        else:
            if pU < H:
                pU += 1
    if f:
        print("YES")
    else:
        print("NO")

if __name__ == "__main__":
    main()