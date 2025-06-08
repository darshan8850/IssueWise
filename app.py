import gradio as gr
from agent.core import run_agent
from config import AVAILABLE_MODELS

async def respond_to_issue(issue_url, branch_name, model_type):
    logs = []
    async for log_msg in run_agent(issue_url, branch_name, model_type):
        logs.append(str(log_msg))

    collapsible_logs = "<details><summary>Click to view agent's used tool logs</summary>\n\n"
    for log in logs:
        collapsible_logs += f"- {log}\n"
    collapsible_logs += "</details>\n\n"

    final_message = f"{collapsible_logs} Agent has successfully processed the issue and posted an update in the comments. Check the GitHub issue for updates."

    return [{"role": "assistant", "content": final_message}]

theme = gr.themes.Soft(
    primary_hue="orange",
    secondary_hue="yellow",
    neutral_hue="zinc",
)

with gr.Blocks(title="OpenSorus – AI Maintainer Agent", theme=theme) as demo:
    gr.Markdown("""
    # OpenSorus – AI Maintainer Agent for GitHub Issues
    
    **Reads the issue. Understands your repo. Replies in seconds.** - _Powered by Multiple AI Models 🧡 & LlamaIndex 🦙_

    Let OpenSorus handle your first-level triage by autonomously pulling context from your codebase and commenting with a helpful fix/suggestion to help your contributors/customers.

    **Note**: Please [install the agent](https://github.com/apps/opensorus) as a GitHub app for a particular repository before using this tool.

    - **Quickest way to assign issues to OpenSorus**: Just mention @opensorus in the GitHub issue comments.
    - Alternatively, use this space to assign the issue by pasting the issue URL below & specifying the primary branch name of your codebase (e.g., main, master, etc.).

                
     _(Drop a ❤️ if this tool made your day a little easier!)_
                
    ---
    """)

    with gr.Row():
        with gr.Column(scale=1):
            issue_url = gr.Textbox(label="🔗 GitHub Issue URL", placeholder="https://github.com/user/repo/issues/123")
            branch_name = gr.Textbox(label="🌿 Branch Name", placeholder="main or dev or feature/xyz")
            model_type = gr.Dropdown(
                choices=[(model["name"], key) for key, model in AVAILABLE_MODELS.items()],
                label="🤖 AI Model",
                value="mistral",
                info="Select which AI model to use for processing the issue"
            )
            submit_btn = gr.Button("🚀 Run Agent", variant="primary")

        with gr.Column(scale=1):
            chatbot = gr.Chatbot(
                label="Task Status",
                type="messages",
                avatar_images=(
                    None,
                    "https://res.cloudinary.com/ivolve/image/upload/v1749307354/OpenSorus-logo_r2bfzw.jpg",
                ),
                height=250,
                resizable=True,
                max_height=400
            )

        submit_btn.click(
            fn=respond_to_issue,
            inputs=[issue_url, branch_name, model_type],
            outputs=chatbot,
            queue=True,
        )

    gr.Markdown("""       
    ---
                
    ### 🛠 How It Works
    1. [Install OpenSorus](https://github.com/apps/opensorus) as a GitHub App.
    2. Configure the app to have access to your particular repository.
    3. Mention @opensorus in any issue's comments.
    4. Alternatively, use this space to paste the issue URL and specify the branch name (e.g., main, master, etc.).
    5. Select your preferred AI model from the dropdown.
    6. Click Run Agent and OpenSorus will fetch issue details, read your code, and post a helpful comment.
    
    > ### _OpenSorus is just like an L1 dev support assistant of your project that never sleeps — and knows your codebase ✨._
    
    ---
""")

if __name__ == "__main__":
    demo.launch()