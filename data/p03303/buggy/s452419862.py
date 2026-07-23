def main():
    s_i = input()
    n_i = int(input())
    ans = ""
    while True:
        if len(s_i) < n_i:
            if n_i == 1:
                break
            else:
                if s_i == "":
                    break
                else:
                    ans += s_i[0]
                    break
        else:
            ans += s_i[:n_i][0]
            s_i = s_i[n_i:]
            print(ans)


if __name__ == "__main__":
    main()