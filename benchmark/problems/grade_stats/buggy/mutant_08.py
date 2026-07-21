def grade_stats(scores):
    ordered = sorted(scores)
    total = 0.0
    count = 0
    for s in ordered:
        total = total + s
        count = count + 1
    return [ordered[0 + 1], ordered[-1], round(total / count, 2)]
