def main():
    n, m = map(int, input().split())
    a_list = list(map(int, input().split()))

    for _ in range(m):
        a_list[a_list.index(max(a_list))] /= 2

    print(sum(a_list))


if __name__ == '__main__':
    main()
