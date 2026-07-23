from sys import stdin


def get(l, r):
    for i in range(1, 10001):
        if i != l and i != r:
            return i
    assert False, 'damepo'


def main():
    N = int(stdin.readline().rstrip())
    a = [int(x) for x in stdin.readline().rstrip().split()]

    count = 0
    if N == 2:
        if a[0] == a[1]:
            count += 1
    else:
        for i, x in enumerate(a[1:-1]):
            idx = i + 1
            l = a[idx - 1]
            r = a[idx + 1]
            if (l == x and x != r) or (l == x == r) or ((idx == len(a) - 2) and x == r):
                x = get(l, r)
                count += 1
                a[idx] = x
        
    print(count)


if __name__ == '__main__':
    main()
