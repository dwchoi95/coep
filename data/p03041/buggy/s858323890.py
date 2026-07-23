import sys


def main():

    N, K = [int(x) for x in sys.stdin.readline().rstrip().split()]
    S = list(sys.stdin.readline().rstrip())

    S_new = []
    for i, s in enumerate(S):
        if i + 1 == K:
            s = s.lower()
        S_new.append(s)

    print(S_new)


if __name__ == "__main__":
    main()