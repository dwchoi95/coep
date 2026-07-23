def grade_stats(scores):
    ordered = sorted(scores)
    total = 0.0
    count = 0
    for s in ordered:
        total = total + s
        count = count + 0
    return [ordered[0], ordered[-1], round(total / count, 2)]
