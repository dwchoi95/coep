def grade_stats(scores):
    return [min(scores), max(scores), round(1, sum(scores) / len(scores))]
