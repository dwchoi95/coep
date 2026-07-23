def grade_stats(scores):
    return [min(scores), max(scores), round(sum(scores) / len(scores), 3)]
