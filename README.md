---
title: IssueWiz - OSS Maintainer Agent
emoji: ⚡️
colorFrom: yellow
colorTo: red
sdk: gradio
sdk_version: 5.33.0
app_file: app.py
pinned: false
license: apache-2.0
short_description: GitHub Issues Maintainer Agent for Open Source Projects
---

# IssueWiz - AI-Powered GitHub Issue Assistant 🤖

IssueWiz is an intelligent GitHub issue assistant that helps maintainers and contributors by automatically analyzing issues, understanding codebase context, and providing helpful responses. It's like having an L1 developer support assistant that never sleeps and knows your codebase inside out.

## 🌟 Features

- **Automatic Issue Analysis**: Understands and classifies GitHub issues
- **Codebase Context**: Pulls relevant code context using LlamaIndex
- **Smart Responses**: Generates helpful, contextual responses using advanced AI models
- **Multiple AI Models**: Supports various AI models including Mistral and OpenAI
- **GitHub Integration**: Seamless integration with GitHub through GitHub App
- **User-Friendly Interface**: Clean Gradio-based web interface

## 🛠 Tech Stack

- **Frontend**: 
  - Gradio (v5.33.0) - For the web interface
  - Custom CSS theming with Soft theme

- **Backend**:
  - Python 3.x
  - LlamaIndex (v0.12.40) - For codebase indexing and context retrieval
  - MistralAI (v1.8.1) - Primary AI model integration
  - OpenAI - Alternative AI model support
  - PyJWT (v2.10.1) - For GitHub App authentication
  - scikit-learn (v1.6.1) - For text processing and analysis
  - requests (v2.32.3) - For API communications
  - python-dotenv (v1.1.0) - For environment configuration
  - cryptography - For secure key handling

## 🚀 Getting Started

### Prerequisites

- Python 3.8 or higher
- GitHub account
- GitHub App credentials (APP_ID and APP_PRIVATE_KEY)

### Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/IssueWise.git
   cd IssueWise
   ```

2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Create a `.env` file in the root directory:
   ```
   APP_ID=your_github_app_id
   APP_PRIVATE_KEY=your_github_app_private_key
   ```

### Running the Application

1. Start the application:
   ```bash
   python app.py
   ```

2. Open your browser and navigate to the provided local URL (typically http://localhost:7860)

## 📝 Usage

1. **Install GitHub App**:
   - Install [IssueWiz GitHub App](https://github.com/apps/IssueWiz)
   - Configure it for your repository

2. **Using the Web Interface**:
   - Enter the GitHub issue URL
   - Specify the branch name (e.g., main, master)
   - Select your preferred AI model
   - Click "Run Agent"

3. **Using GitHub Comments**:
   - Simply mention @IssueWiz in any issue's comments
   - The agent will automatically process the issue

## 🔧 Configuration

The application can be configured through:

- `.env` file for environment variables
- `config.py` for application settings
- Model selection in the web interface

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📄 License

This project is licensed under the terms of the license included in the repository.

## 🙏 Acknowledgments

- LlamaIndex for the powerful codebase indexing capabilities
- MistralAI and OpenAI for their advanced language models
- Gradio for the beautiful web interface framework
