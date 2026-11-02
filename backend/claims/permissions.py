from common.exceptions import forbidden, missing


def require_participant(claim, user):
    if user.pk not in (claim.applicant_id, claim.post.publisher_id):
        missing()


def require_publisher(claim, user):
    require_participant(claim, user)
    if user.pk != claim.post.publisher_id:
        forbidden()
