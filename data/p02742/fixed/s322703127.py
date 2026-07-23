



def main():
    h, w = map(int, input().split())
    if h == 1 or w == 1:
        ans = 1
    elif h % 2 == 0:
        ans = (h 
    elif w % 2 == 0:
        ans = (w 
    else:
        ans = h * (w 
    print("%d" % ans)


if __name__ == '__main__':
    main()
