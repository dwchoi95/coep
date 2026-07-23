from heapq import heappop, heappush
import sys


class SSSP:
    
    def __init__(self, graph):
        self.size = len(graph)
        self.tree = []
        self.weights = [0] * self.size
        self._search(graph)

    def weight(self, n):
        return self.weights[n]

    def _search(self, graph):
        h = []
        count = 1
        for i, w in graph[0]:
            heappush(h, (w, 0, i))

        while count < self.size:
            while len(h) > 0:
                weight, src, dst = heappop(h)
                if self.weights[dst] == 0 and dst > 0:
                    self.weights[dst] = weight
                    count += 1
                    self.tree.append((src, dst))
                    for i, w in graph[dst]:
                        if self.weights[i] == 0 and dst > 0:
                            heappush(h, (w+weight, dst, i))
                    break


def run():
    n = int(input())

    nodes = [None] * n
    for line in sys.stdin:
        id_, deg, *edges = [int(i) for i in line.split()]
        nodes[id_] = []
        for _ in range(deg):
            tgt, wgt, *edges = edges
            nodes[id_].append((tgt, wgt))

    st = SSSP(nodes)
    for node in range(n):
        print('{} {}'.format(node, st.weight(node)))


if __name__ == '__main__':
    run()

