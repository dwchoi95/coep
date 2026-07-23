def main():
    h, w, m = map(int, input().split())
    lsh = [0] * h
    lsw = [0] * w

    bom = set()
    for _ in range(m):
        m1, m2 = map(int, input().split())
        lsh[m1 - 1] += 1
        lsw[m2 - 1] += 1
        bom.add((m1-1, m2-1))

    lshmax = max(lsh)
    lswmax = max(lsw)

    hin = [i for i in range(h) if lsh[i] == lshmax]
    win = [i for i in range(w) if lsw[i] == lswmax]

    for i in hin:
        for j in win:
            if (i, j) not in bom:
                print(lshmax + lswmax)
                exit(0)
    else:
        print(lshmax + lswmax -1)


if __name__ == '__main__':
    main()