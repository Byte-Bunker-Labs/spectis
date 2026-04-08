"""Prompt routing and agent selection service.

Routes natural-language prompts to the best-matching registered agent
using keyword scoring against each agent's keyword list.
"""

from app.models.agent import Agent


def score_prompt_for_agent(prompt: str, agent: Agent) -> float:
    """Score how well a prompt matches an agent's keyword list.

    Returns a float between 0.0 and 1.0 representing match confidence.
    """
    if not agent.keywords:
        return 0.0

    prompt_lower = prompt.lower()
    keywords = [k.lower() for k in agent.keywords]
    matches = sum(1 for kw in keywords if kw in prompt_lower)

    if not keywords:
        return 0.0

    return matches / len(keywords)


def select_agent(prompt: str, agents: list[Agent]) -> tuple[Agent | None, float]:
    """Select the best-matching agent for a prompt.

    Returns (agent, confidence) or (None, 0.0) if no match found.
    Only considers approved agents.
    """
    best_agent = None
    best_score = 0.0

    for agent in agents:
        if agent.status != "approved":
            continue
        score = score_prompt_for_agent(prompt, agent)
        if score > best_score:
            best_score = score
            best_agent = agent

    return best_agent, best_score
