import asyncio
from typing import Any, List

from agent import create_agent

def load_model(code_dir: str) -> Any:
    """
    DRUM hook: called at container startup to load a model object.
    Returning a Python object here prevents DRUM from requiring .pkl/.onnx/etc.
    """
    # code_dir is typically /opt/code, but we don't need it since we import from it.
    agent = create_agent()
    return agent

async def _run(agent, prompts: List[str]) -> List[str]:
    out = []
    for p in prompts:
        try:
            result = await agent.run(p)
            out.append(result.output)
        except Exception as e:
            out.append(f"Agent error: {type(e).__name__}: {str(e)}")
    return out

def score(data, model, **kwargs):
    """
    DRUM hook: called for inference.
    'model' is whatever load_model() returned (our agent instance).
    """
    # Normalize input to list[str]
    if isinstance(data, list):
        prompts = [str(x) for x in data]
    elif hasattr(data, "to_dict"):
        try:
            rows = data.to_dict(orient="records")
            prompts = [str(r.get("prompt", r)) for r in rows]
        except Exception:
            prompts = [str(data)]
    else:
        prompts = [str(data)]

    return asyncio.run(_run(model, prompts))
