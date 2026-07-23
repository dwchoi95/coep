



def main():
    h, w = map(int, input().split())
    ans = (h * w) / 2
    if h % 2 == w % 2 == 1:
        ans = ans + 1
    print("%d" % ans)


if __name__ == '__main__':
    main()
