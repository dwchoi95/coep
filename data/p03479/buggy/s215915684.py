


def main(min_limit, max_limit):
    result = []
    i = min_limit

    while(i < max_limit + 1):
        result.append(i)
        i = i * 2
    print(len(result))
    print(result)


if __name__ == "__main__":
    min_limit, max_limit = [int(val) for val in input().split()]
    main(min_limit, max_limit)