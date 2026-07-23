def grade_stats(scores):
    lo = 0
    hi = 0
    total = 0
    for s in scores:
        if s < lo:
            lo = s
        if s > hi:
            hi = s
        total += s
    return [lo, hi, round(total / len(scores), 2)]
