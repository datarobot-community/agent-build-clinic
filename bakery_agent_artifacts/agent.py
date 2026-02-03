import os
import datarobot as dr
from pydantic import BaseModel, Field
from pydantic_ai import Agent, RunContext
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider

class ForecastInput(BaseModel):
    forecast_date: str = Field(..., description="YYYY-MM-DD format")
    item_id: str = Field(..., description="Item to forecast")

def create_agent():
    """
    Factory that builds and returns a configured pydantic-ai Agent.
    Called from custom.load_model() so DRUM can load a "model object".
    """
    # Runtime params (configure in DataRobot Runtime Parameters / env vars)
    forecast_deployment_id = os.environ.get("FORECAST_DEPLOYMENT_ID")
    forecast_dataset_id = os.environ.get("FORECAST_DATASET_ID")
    llm_model_id = os.environ.get("LLM_MODEL_ID", "azure/gpt-5-2025-08-07")
    llm_api_key = os.environ.get("LLM_API_KEY")  # optional override

    dr_client = dr.Client()

    # LLM Gateway base URL
    llmgw_base_url = dr_client.endpoint.rstrip("/") + "/genai/llmgw"

    provider = OpenAIProvider(
        api_key=llm_api_key or dr_client.token,
        base_url=llmgw_base_url,
    )
    model = OpenAIChatModel(llm_model_id, provider=provider)

    async def get_bakery_forecast(ctx: RunContext, input_data: ForecastInput) -> str:
        if not forecast_deployment_id or not forecast_dataset_id:
            return (
                "Forecast unavailable: missing configuration. "
                "Set FORECAST_DEPLOYMENT_ID and FORECAST_DATASET_ID as runtime parameters."
            )
        try:
            deployment = dr.Deployment.get(forecast_deployment_id)
            dataset = dr.Dataset.get(forecast_dataset_id)

            job = dr.BatchPredictionJob.score(
                deployment=deployment,
                intake_settings={"type": "dataset", "dataset": dataset},
                passthrough_columns=["date", "item_id"],
            )
            job.wait_for_completion()
            return f"Forecast generated for item_id={input_data.item_id} on {input_data.forecast_date}."
        except Exception as e:
            return f"Forecast unavailable: {type(e).__name__}: {str(e)}"

    agent = Agent(
        model=model,
        tools=[get_bakery_forecast],
        system_prompt=(
            "You are a Bakery Supply Chain Agent. Help manage orders and stock. "
            "When relevant, call tools to fetch forecasts."
        ),
    )
    return agent
