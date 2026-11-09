"""Reaction HTTP Route Definitions (Router and Route Table)."""

from raft import route, Router
from schemas import ReactionToggleSchema, ReactionResponseSchema
from views.reactions import toggle_reaction_view, get_reaction_status_view

# Demonstrates Router decorators
router = Router(prefix="/api/reactions")
router.post("/toggle", request_body=ReactionToggleSchema, responses={200: ReactionResponseSchema})(toggle_reaction_view)
router.get("/status")(get_reaction_status_view)

# Demonstrates route() table list
routes = [
    route("/api/reactions/toggle", toggle_reaction_view, methods=["POST"], request_body=ReactionToggleSchema, responses={200: ReactionResponseSchema}),
    route("/api/reactions/status", get_reaction_status_view, methods=["GET"]),
]
