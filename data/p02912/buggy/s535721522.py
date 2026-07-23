from sys import stdin
import heapq


def main():
    N, M = [int(x) for x in stdin.readline().rstrip().split()]
    As = []
    for i in [int(x) for x in stdin.readline().rstrip().split()]:
        heapq.heappush(As, i)
    for _ in range(M):
        x = heapq.heappop(As)
        heapq.heappush(As, x / 2)
    print(sum([int(x) for x in As]))


if __name__ == "__main__":
    main()
