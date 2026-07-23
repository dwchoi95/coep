

import cmath


def outer_product(v1, v2):
    return v1.real * v2.imag - v1.imag * v2.real


def in_place_sort_points_ccw(points):
    points.sort(key=cmath.phase)


def area_polygon(n, points):
    in_place_sort_points_ccw(points)
    s = sum(outer_product(points[i], points[(i + 1) % n])
            for i in range(n)) / 2.0
    return s


def main():
    n = int(input())
    ps = [complex(*map(float, input().split())) for _ in range(n)]
    s = area_polygon(n, ps)
    print("{:.1f}".format(s))


if __name__ == '__main__':
    main()