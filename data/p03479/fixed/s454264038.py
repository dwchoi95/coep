def solve(X, Y):
    tmp = X
    ans = 0
    while tmp <= Y:
        ans += 1
        tmp *= 2
    return ans

def main():
    X, Y = map(int, input().split())
    ans = solve(X, Y)
    print(ans)

if __name__ == "__main__":
    main()