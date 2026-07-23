def resolve():
    h, w = map(int, input().split())
    dy = h 
    if h == 1 or w == 1:
        count = 1
    elif h % 2 == 1:
        count = w * dy + (w - (w 
    else:
        count = w * dy

    print(count)


if __name__ == '__main__':
    resolve()