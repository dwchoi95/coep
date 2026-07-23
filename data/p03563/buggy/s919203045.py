def newrating(r , g):

    return (r + g) / 2

def main():
    r = int(input())
    g = int(input())
    print(newrating(r , g))

if __name__ == '__main__':
    main()