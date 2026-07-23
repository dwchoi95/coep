X, Y = map(int, input().split())

crane = (4 * X - Y) / 2
turtle = (Y - 2 * X) / 2


def is_integer_num(n):
    if isinstance(n, int):
        return True
    if isinstance(n, float):
        return n.is_integer()
    return False


if is_integer_num(crane) and crane >= 0 and is_integer_num(turtle) and turtle >= 0:
    print("Yes")

else:
    print("No")
