"""All mutable personal data lives in the current Streamlit session."""

def new_interview():
    return {"question": None, "turns": [], "feedback": None, "guides": [],
            "question_number": 0, "attempt": 1, "ended": False, "summary": None,
            "draft_version": 0}


def initialize(state):
    defaults = {"input_fingerprint": None, "context": None, "optimization": None,
                "matching": None, "interview": new_interview(), "accepted": {}}
    for key, value in defaults.items():
        if key not in state:
            state[key] = value


def invalidate(state, fingerprint: str) -> bool:
    initialize(state)
    if state["input_fingerprint"] == fingerprint:
        return False
    had_context = state["context"] is not None
    state.update(input_fingerprint=fingerprint, context=None, optimization=None,
                 matching=None, interview=new_interview(), accepted={})
    # Drop stale drafts and acceptance widgets, not only their display containers.
    for key in list(state):
        if str(key).startswith(("accept_", "answer_")):
            del state[key]
    return had_context
