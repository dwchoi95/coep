import sys


def main():
    sys.stdin.readline()
    list1 = list(map(str, sys.stdin.readline().split()))
    list.sort(list1, reverse=True)
    print(' '.join(list1))
    return


if __name__ == '__main__':
    main()

