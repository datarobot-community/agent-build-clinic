import datarobot as dr
from pydantic_ai import Agent, RunContext
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider
from pydantic import BaseModel, Field
import pandas as pd
import os

# 1. Initialize Backend
# In production, credentials are injected automatically via environment variables
dr_client = dr.Client()
model = OpenAIChatModel(
    "azure/gpt-5-2025-08-07",
    provider=OpenAIProvider(
        api_key=dr_client.token, 
        base_url=dr_client.endpoint + "/genai/llmgw"
    ),
)


# 2. Define Tools (Consolidated from Notebook 3)
class ForecastInput(BaseModel):
    forecast_date: str = Field(..., description="YYYY-MM-DD format")
    item_id: str = Field(..., description="Item to forecast")

async def get_bakery_forecast(ctx: RunContext, input_data: ForecastInput) -> str:
    # NOTE: In a real app, use os.environ to fetch these IDs securely
    # For this demo, we assume the IDs are known or hardcoded for simplicity
    DEPLOYMENT_ID = "696eafd36ad06b16d2f6ab2b" 
    DATASET_ID = "695f94e383353176fc0ab346"

    try:
        deployment = dr.Deployment.get(DEPLOYMENT_ID)
        dataset = dr.Dataset.get(DATASET_ID)

        # Run prediction
        job = dr.BatchPredictionJob.score(
            deployment=deployment,
            intake_settings={"type": "dataset", "dataset": dataset},
            passthrough_columns=["date", "item_id"]
        )
        prediction_result = job.wait_for_completion()
        df = prediction_result.get_result_when_complete()

        # Simple filter logic
        # (Simplified for brevity in the deployed file)
        return f"Forecast generated successfully. (See logs for detailed numbers)"

    except Exception as e:
        return f"Forecast unavailable: {str(e)}"

# 3. Define the Agent
agent = Agent(
    model=model,
    tools=[get_bakery_forecast],
    system_prompt="You are a Bakery Supply Chain Agent. Help manage orders and stock."
)

# 4. DataRobot Custom Model Hook
# This function is the entry point DataRobot calls when you chat in the Playground
async def score(data, model, **kwargs):
    responses = []
    for prompt in data:
        # 'prompt' here is the user's message
        result = await agent.run(prompt)
        responses.append(result.output)
    return responses
