


def main():
    
    a, b, c, d = map(int, input().split())
    if a+b < c+d:
        print("Right")
    if a+b == c+d:
        print("Balanced")
    else:
        print("Left")


if __name__ == "__main__":
    main()
