import heapq


def main():
    n, m = map(int, input().split())
    a_list = list(map(lambda x: -int(x), input().split()))

    heapq.heapify(a_list)
    for _ in range(m):
        a = heapq.heappop(a_list)
        heapq.heappush(a_list, -(-a 

    print(-sum(a_list))


if __name__ == '__main__':
    main()
