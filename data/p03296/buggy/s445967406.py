from sys import stdin


def get(l, r):
    for i in range(1, 10001):
        if i != l and i != r:
            return i
    assert False, 'damepo'


def main():
    N = int(stdin.readline().rstrip())
    a = [int(x) for x in stdin.readline().rstrip().split()]
    l = a[0]
    count = 0
    for i, x in enumerate(a[1:-1]):
        idx = i + 1
        l = a[idx - 1]
        r = a[idx + 1]
        if l != x != r:
            pass
        elif (idx + 3) < len(a):
            if x == r == a[idx + 2] and x != a[idx + 3]:
                continue
        elif (idx + 2) < len(a):
            if x == r == a[idx + 2]:
                continue
        x = get(l, r)
        count += 1
        a[idx] = x
    
    print(count)


if __name__ == '__main__':
    main()
