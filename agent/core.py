import json
from mistralai import Mistral
from openai import OpenAI
from anthropic import Anthropic
from agent.agent_config import prompts
from agent.agent_config import tool_schema
from config import AVAILABLE_MODELS
from tools.code_index import retrieve_context
from tools.github_tools import fetch_github_issue, get_issue_details, post_comment

tools = tool_schema.tools
names_to_functions = {
    "fetch_github_issue": fetch_github_issue,
    "get_issue_details": get_issue_details,
    "retrieve_context": retrieve_context,
    "post_comment": post_comment,
}

allowed_tools = set(names_to_functions.keys())

system_message = prompts.system_message

def get_model_client(model_type):
    """Get the appropriate client based on the model type."""
    model_config = AVAILABLE_MODELS.get(model_type)
    if not model_config or not model_config["api_key"]:
        raise ValueError(f"Invalid model type or missing API key for {model_type}")
    
    if model_type == "mistral":
        return Mistral(api_key=model_config["api_key"]), model_config["model"]
    elif model_type == "openai":
        return OpenAI(api_key=model_config["api_key"]), model_config["model"]
    elif model_type == "claude":
        return Anthropic(api_key=model_config["api_key"]), model_config["model"]
    else:
        raise ValueError(f"Unsupported model type: {model_type}")

async def run_agent(issue_url: str, branch_name: str = "main", model_type: str = "mistral"):
    """
    Run the agent workflow on a given GitHub issue URL.
    """
    MAX_STEPS = 5
    tool_calls = 0
    issue_description_cache = None

    client, model = get_model_client(model_type)

    user_message = {
        "role": "user",
        "content": f"Please suggest a fix on this issue {issue_url} and use {branch_name} branch for retrieving code context."
    }
    messages = [system_message, user_message]

    yield f"⚡️ OpenSorus agent started using {AVAILABLE_MODELS[model_type]['name']}..."

    while True:
        if model_type == "mistral":
            response = client.chat.complete(
                model=model,
                messages=messages,
                tools=tools,
                tool_choice="any",
            )
            msg = response.choices[0].message
        elif model_type == "openai":
            response = client.chat.completions.create(
                model=model,
                messages=messages,
                tools=tools,
                tool_choice="auto",
            )
            msg = response.choices[0].message
        elif model_type == "claude":
            response = client.messages.create(
                model=model,
                messages=messages,
                tools=tools,
            )
            msg = response.content[0]

        messages.append(msg)

        if hasattr(msg, "tool_calls") and msg.tool_calls:
            for tool_call in msg.tool_calls:
                function_name = tool_call.function.name
                function_params = json.loads(tool_call.function.arguments)
                if function_name in allowed_tools:
                    yield f"🔧 Agent is calling tool: `{function_name}`"
                    function_result = names_to_functions[function_name](**function_params)
                    tool_calls += 1

                    if function_name == "get_issue_details" and isinstance(function_result, dict):
                        issue_title = function_result.get("title")
                        issue_body = function_result.get("body")
                        issue_description_cache = issue_title + "\n" + issue_body if issue_title or issue_body else None
                        yield "📝 Issue description cached."

                    if function_name == "retrieve_context":
                        if "issue_description" in function_params:
                            if (
                                issue_description_cache
                                and (function_params["issue_description"] != issue_description_cache)
                            ):
                                yield "⚠️ Overriding incorrect issue_description with correct one from cache."
                                function_params["issue_description"] = issue_description_cache
                                function_result = names_to_functions[function_name](**function_params)

                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": str(function_result)
                    })

                    if function_name == "post_comment":
                        yield "✅ Comment posted. Task complete."
                        return

                else:
                    yield f"Agent tried to call unknown tool: {function_name}"
                    tool_error_msg = (
                        f"Error: Tool '{function_name}' is not available. "
                        "You can only use the following tools: fetch_github_issue, get_issue_details, post_comment."
                    )
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": tool_error_msg
                    })
            if tool_calls >= MAX_STEPS:
                yield f"Agent stopped after {MAX_STEPS} tool calls to protect against rate limiting."
                break
        else:
            yield f"OpenSorus (final): {msg.content}"
            break

    yield "Task Completed"