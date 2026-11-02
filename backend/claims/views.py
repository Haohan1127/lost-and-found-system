from rest_framework.views import APIView
from common.responses import ok
from common.serializers import EmptyInput, validated, paginate
from workflows import claim_workflow
from . import serializers as s
from .selectors import get_claim, my_claims, message_batch
from .messages import send_message
from .matching import match_posts


class ClaimCreateView(APIView):
    def post(self, request):
        data = validated(s.CreateClaimInput, request.data)
        claim = claim_workflow.create_claim(request.user, **data)
        return ok(s.claim_view(claim), 201)


class ClaimDetailView(APIView):
    def get(self, request, claim_id):
        validated(EmptyInput, request.query_params)
        return ok(s.claim_view(get_claim(claim_id, request.user)))


class MyClaimsView(APIView):
    def get(self, request):
        query = validated(s.ClaimListQuery, request.query_params)
        return ok(paginate(my_claims(request.user, query), query, s.claim_view))


class ClaimActionView(APIView):
    def post(self, request, claim_id, action):
        schemas = {"accept": s.AcceptInput, "reject": s.RejectInput, "cancel": EmptyInput, "confirm-handover": EmptyInput}
        functions = {"accept": claim_workflow.accept_claim, "reject": claim_workflow.reject_claim,
                     "cancel": claim_workflow.cancel_claim, "confirm-handover": claim_workflow.confirm_handover}
        data = validated(schemas[action], request.data)
        return ok(s.claim_view(functions[action](request.user, claim_id, **data)))


class ClaimMessagesView(APIView):
    def get(self, request, claim_id):
        claim = get_claim(claim_id, request.user)
        query = validated(s.MessageQuery, request.query_params)
        items, next_id, more = message_batch(claim, query)
        return ok({"items": [s.message_view(row) for row in items], "next_after_id": next_id, "has_more": more})

    def post(self, request, claim_id):
        data = validated(s.MessageInput, request.data)
        return ok(s.message_view(send_message(request.user, claim_id, **data)), 201)


class MatchesView(APIView):
    def get(self, request, post_id):
        query = validated(s.MatchQuery, request.query_params)
        return ok(match_posts(request.user, post_id, query["limit"]))
