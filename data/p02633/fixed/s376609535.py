






def main():
    x = int(input())
    k = 1
    while ( x * k ) % 360:
        k += 1
    print(k)
    return

if __name__ == "__main__":
    main()