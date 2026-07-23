def grade_stats(scores):
    ordered = sorted(scores)
    mid = ordered[len(ordered) // 2]
    return [ordered[0], ordered[-1], round(mid, 2)]
