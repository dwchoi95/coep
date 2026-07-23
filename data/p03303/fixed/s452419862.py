def main():
    s_i = input()
    n_i = int(input())
    ans = ""
    while True:
        if len(s_i) < n_i:
            if s_i != "":
               ans += s_i[0]
               break
            else:
                break
        else:
            ans += s_i[:n_i][0]
            s_i = s_i[n_i:]
    print(ans)


if __name__ == "__main__":
    main()