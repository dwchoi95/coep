def main():
    a, b, c = map(int, input().split() )

    if a == b + c | b == c + a | c == a + b:
        print("Yes")
    else:
        print("No")

if __name__ == "__main__":
    main()