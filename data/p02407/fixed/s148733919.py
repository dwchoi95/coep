def main():
    n = int(input())
    a = map(int, input().split())
    print(" ".join(map(str, list(a)[::-1])))

if __name__ == "__main__":
    main()