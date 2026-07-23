def resolve():
    h, w = map(int, input().split())
    dy = h 
    if h == 1:
        count = w 
    elif w == 1:
        count = h 
    elif h % 2 == 1:
        count = w * dy + (w-1)
    else:
        count = w * dy

    print(count)

if __name__ == '__main__':
    resolve()