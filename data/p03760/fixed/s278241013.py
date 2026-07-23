


def solve():
    o = input()
    e = input()

    for l, r in zip(o, e):
        print('{}{}'.format(l, r), end="")

    if len(o) != len(e):
        print(o[-1])
    else:
        print()


if __name__ == '__main__':
    solve()
