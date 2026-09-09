"""
SmartCiti.X mentor fabric — LangChain 1.0 / LangGraph 1.0 wiring reference.

┌───────────────────────────────────────────────────────────────────────────┐
│ NOT EXECUTED. This file has never been run: it needs model credentials    │
│ and the langchain/langgraph packages, neither of which exist in the       │
│ environment where the rest of this bundle was built and tested. Treat it  │
│ as a reviewed design, not as verified code. Everything in agent.mjs,      │
│ evals.mjs and router.mjs IS tested (16 checks) and is the authority on    │
│ behaviour; this file adapts a framework to that contract.                 │
└───────────────────────────────────────────────────────────────────────────┘

Maps ACP-11 §12.2 onto the framework:
  supervisor node  -> Chris, for cross-trade and unrouted traffic
  in-hall handoff  -> Command(goto=...) swarm transfers between hall mentors
  durable execution-> checkpointer, so a mentor conversation survives across
                      sessions and devices (the reason LangGraph is here at all)
  middleware       -> PII redaction, scope guard, HITL escalation

KNOWN RISK — two-language guard duplication. The scope guard, PII redaction and
rung clamping are tested in agent.mjs. Re-implementing them in Python means two
copies of a security-relevant rule that can drift. Two ways out, pick one before
building:
  (a) run the fabric in JS on @langchain/langgraph and import agent.mjs directly
      — one implementation, one test suite, no drift; or
  (b) keep Python and make the guards a single service both languages call,
      with agent.mjs's tests running against that service in CI.
Do not simply port the functions by hand.
"""
from __future__ import annotations

import re
from typing import Annotated, Literal, TypedDict

from langchain.agents import create_agent          # LangChain 1.0
from langchain.agents.middleware import AgentMiddleware
from langgraph.graph import StateGraph, START, END
from langgraph.types import Command
from langgraph.checkpoint.postgres import PostgresSaver

MAX_HANDOFFS = 3           # must match router.mjs
FORBIDDEN_ACTIONS = {      # must match agent.mjs
    "dial.set_setpoint", "dial.pin", "profile.write", "gate.certify",
    "profile.read_other_learner", "registry.write", "override.apply",
}


class MentorState(TypedDict):
    messages: Annotated[list, "append"]
    learner_id: str
    hall: str
    dial: dict                 # READ-ONLY snapshot from the control plane
    requested_rung: int
    scaffold_ceiling: int
    handoffs: int
    audit: Annotated[list, "append"]


# --------------------------------------------------------------- middleware --
class ScopeGuard(AgentMiddleware):
    """Mentors voice the system; they never steer it (ACP-09 single-writer)."""

    def after_model(self, state, runtime):
        calls = [tc["name"] for tc in state["messages"][-1].tool_calls or []]
        bad = [c for c in calls if c in FORBIDDEN_ACTIONS]
        if bad:
            state["audit"].append({"event": "scope_violation", "actions": bad})
            return {"messages": [{
                "role": "assistant",
                "content": ("That's not something I can do — I coach, I don't change "
                            "your settings or your record. I'll flag it for your instructor."),
            }]}
        return None


class RungDiscipline(AgentMiddleware):
    """Never serve deeper help than was asked for, or than the ladder allows."""

    def after_model(self, state, runtime):
        served = state.get("served_rung", 0)
        ceiling = state["scaffold_ceiling"]
        asked = state["requested_rung"]
        if served > min(asked, ceiling):
            state["audit"].append({"event": "over_help", "served": served, "asked": asked})
            return {"served_rung": min(asked, ceiling), "retry": True}
        return None


PII = [
    (re.compile(r"\b\d{3}-\d{2}-\d{4}\b"), "[redacted-id]"),
    (re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.]{2,}\b"), "[redacted-email]"),
    (re.compile(r"\b(?:\+?1[-. ]?)?\(?\d{3}\)?[-. ]\d{3}[-. ]\d{4}\b"), "[redacted-phone]"),
]


class PIIRedaction(AgentMiddleware):
    """Runs on the way in AND the way out — models leak too."""

    def _scrub(self, text: str) -> str:
        for pattern, repl in PII:
            text = pattern.sub(repl, text)
        return text

    def before_model(self, state, runtime):
        last = state["messages"][-1]
        return {"messages": [{**last, "content": self._scrub(last.content)}]}

    def after_model(self, state, runtime):
        last = state["messages"][-1]
        return {"messages": [{**last, "content": self._scrub(last.content)}]}


ESCALATIONS = re.compile(
    r"\b(injur|bleeding|electrocut|fell from|unconscious|ambulance|"
    r"kill myself|hurt myself|harass|threaten)", re.I)


class HumanEscalation(AgentMiddleware):
    """Hand to a human instructor and stop — do not coach through an incident."""

    def before_model(self, state, runtime):
        if ESCALATIONS.search(state["messages"][-1].content):
            state["audit"].append({"event": "escalated"})
            return Command(goto=END, update={"messages": [{
                "role": "assistant",
                "content": "I'm getting a human instructor on this right now. Stay where you are.",
            }]})
        return None


MIDDLEWARE = [PIIRedaction(), HumanEscalation(), ScopeGuard(), RungDiscipline()]


# ------------------------------------------------------------------ mentors --
def build_mentor(spec: dict):
    """One hall mentor. `spec` carries persona, union, KB retriever and tools.

    A mentor version is (model, KB rev, middleware config) — bump it on ANY of
    the three, and re-run the eval harness. Including "small" prompt edits.
    """
    return create_agent(
        model=spec["model"],
        tools=spec["tools"],                     # read-only registry + KB tools
        system_prompt=spec["persona"],
        middleware=MIDDLEWARE,
    )


def hall_handoff(target: str):
    """Swarm transfer inside a hall — crisp boundaries, 1-2 LLM calls."""

    def _transfer(state: MentorState) -> Command[Literal["supervisor"]]:
        if state["handoffs"] >= MAX_HANDOFFS:
            # Recursion guard. Without this two mentors will pass a learner
            # back and forth; router.mjs has the tested version of this rule.
            return Command(goto="supervisor",
                           update={"audit": [{"event": "guard_tripped"}]})
        return Command(goto=target, update={"handoffs": state["handoffs"] + 1})

    return _transfer


def build_fabric(mentors: dict, halls: dict, checkpoint_uri: str):
    """Hub-hybrid: Chris supervises across trades, mentors swarm within a hall."""
    graph = StateGraph(MentorState)

    graph.add_node("supervisor", build_mentor(mentors["chris"]))
    for mentor_id, spec in mentors.items():
        if mentor_id != "chris":
            graph.add_node(mentor_id, build_mentor(spec))

    graph.add_edge(START, "supervisor")
    graph.add_conditional_edges(
        "supervisor",
        lambda s: s.get("route_to", END),
        {mid: mid for mid in mentors if mid != "chris"} | {END: END},
    )
    for hall, members in halls.items():
        for mentor_id in members:
            graph.add_conditional_edges(
                mentor_id,
                lambda s: s.get("handoff") or END,
                {peer: peer for peer in members if peer != mentor_id} | {END: END},
            )

    # Durable execution: a learner resumes a mentor conversation days later,
    # on another device, without losing context. This is the reason LangGraph
    # is in the stack rather than plain LangChain.
    return graph.compile(checkpointer=PostgresSaver.from_conn_string(checkpoint_uri))


# ----------------------------------------------------------------- rollout ---
# Ship hall by hall (ACP-13 §14.2): canary 1 hall (5% of network) -> 5 halls ->
# all 33, with automatic rollback on ACP-08 stop conditions. No mentor version
# reaches a canary until it has passed all five gates in evals.mjs.
PILOT_HALLS = ["welders", "ironworkers"]
