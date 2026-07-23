

import sys

class DGatheringChildren:
    def solve(self):
        s = input().strip()
        n = len(s)
        i = 0
        last = 0
        ans = [0] * n
        while i < n - 1:
            if s[i] == 'R' and s[i + 1] == 'L':
                ans[i + 1] += 1
                for j in range(last, i + 1):
                    if (i - j) % 2 == 0:
                        ans[i] += 1
                    else:
                        ans[i + 1] += 1
                k = i + 2
                while k < n and s[k] == 'L':
                    if (k - i) % 2 == 0:
                        ans[i] += 1
                    else:
                        ans[i + 1] += 1
                    k += 1

                last = k
                i += 1

            i += 1

        print(*ans)

solver = DGatheringChildren()
input = sys.stdin.readline

solver.solve()
