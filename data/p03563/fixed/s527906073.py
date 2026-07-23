import sys
import os


def main():
    if os.getenv("LOCAL"):
        sys.stdin = open("input.txt", "r")

    R = float(sys.stdin.readline().rstrip())
    G = float(sys.stdin.readline().rstrip())
    print(int(R+(G-R)*2))


if __name__ == '__main__':
    main()
