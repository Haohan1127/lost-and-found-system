import unicodedata
from datetime import timedelta
from common.exceptions import conflict, forbidden
from posts.selectors import visible_post, list_match_candidates
from posts.serializers import post_summary


def title_bigrams(title):
    text = "".join(ch for ch in title.lower() if not ch.isspace() and not unicodedata.category(ch).startswith("P"))
    return {text[i:i + 2] for i in range(len(text) - 1)}


def score_candidate(source, candidate):
    score, reasons = 40, ["category_same"]
    if source.location_id == candidate.location_id:
        score += 30
        reasons.append("location_same")
    if abs(source.occurred_at - candidate.occurred_at) <= timedelta(hours=72):
        score += 20
        reasons.append("time_near")
    if title_bigrams(source.title) & title_bigrams(candidate.title):
        score += 10
        reasons.append("keyword_overlap")
    return score, reasons


def match_posts(user, post_id, limit):
    source = visible_post(post_id, user)
    if source.publisher_id != user.pk:
        forbidden()
    if source.status != "open":
        conflict("仅进行中的本人信息可以查找匹配")
    scored = [(candidate, *score_candidate(source, candidate)) for candidate in list_match_candidates(source)]
    scored.sort(key=lambda row: (row[1], row[0].created_at, row[0].pk), reverse=True)
    return {"source_post_id": str(source.pk), "items": [
        {"post": post_summary(post), "score": score, "reasons": reasons} for post, score, reasons in scored[:limit]
    ]}
