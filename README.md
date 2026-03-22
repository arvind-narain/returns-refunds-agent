# Returns & Refunds Agent - AgentCore Runtime

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![AWS](https://img.shields.io/badge/AWS-Bedrock-orange.svg)](https://aws.amazon.com/bedrock/)

A production-ready AI agent for handling customer returns and refunds, built with Amazon Bedrock AgentCore Runtime.

## 🎯 Overview

This project demonstrates a complete end-to-end implementation of an enterprise-grade AI agent with:

- **🧠 Memory Integration** - Persistent conversation history and user preferences
- **🔗 Gateway Integration** - External API calls via Lambda functions
- **📚 Knowledge Base** - Document retrieval for policy information
- **🛠️ Custom Tools** - Business logic for eligibility and refund calculations
- **☁️ Production Deployment** - Serverless on AgentCore Runtime
- **📊 Full Observability** - CloudWatch Logs, X-Ray traces, GenAI dashboards

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    AgentCore Runtime                         │
│  ┌──────────────────────────────────────────────────────┐   │
│  │         Returns & Refunds Agent                      │   │
│  │  • Memory (Preferences, History, Summaries)          │   │
│  │  • Gateway (Order Lookup via Lambda)                 │   │
│  │  • Knowledge Base (Policy Documents)                 │   │
│  │  • Custom Tools (Eligibility, Refund Calc)           │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
         │                    │                    │
         ▼                    ▼                    ▼
   AgentCore            AgentCore            Lambda Function
     Memory              Gateway            (Order Lookup)
```

## 📋 Prerequisites

- AWS Account with appropriate permissions
- Python 3.10+
- AWS CLI configured
- Bedrock model access (Claude Sonnet 4.5)

## 🚀 Quick Start

### 1. Clone the Repository

```bash
git clone https://github.com/arvind-narain/returns-refunds-agent.git
cd returns-refunds-agent
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Deploy Infrastructure

```bash
# Create Memory
python3 src/infrastructure/03_create_memory.py
python3 src/infrastructure/04_seed_memory.py

# Setup Authentication
python3 src/infrastructure/08_create_cognito.py

# Create IAM Roles
python3 src/infrastructure/09_create_gateway_role.py
python3 src/infrastructure/16_create_runtime_role.py

# Setup Gateway
python3 src/infrastructure/10_create_lambda.py
python3 src/infrastructure/11_create_gateway.py
python3 src/infrastructure/12_add_lambda_to_gateway.py
```

### 4. Deploy Agent

```bash
# Deploy to AgentCore Runtime
python3 scripts/19_deploy_agent.py

# Check deployment status
python3 scripts/20_check_status.py

# Test the agent
python3 scripts/21_invoke_agent.py
```

### 5. Launch UI

```bash
cd src/ui
./run_streamlit.sh
```

Access at: http://localhost:8501

## 📁 Project Structure

```
returns-refunds-agent/
├── src/
│   ├── agents/              # Agent implementations
│   │   ├── 01_returns_refunds_agent.py
│   │   ├── 06_memory_enabled_agent.py
│   │   ├── 14_full_agent.py
│   │   └── 17_runtime_agent.py
│   ├── infrastructure/      # AWS infrastructure setup
│   │   ├── 03_create_memory.py
│   │   ├── 04_seed_memory.py
│   │   ├── 08_create_cognito.py
│   │   ├── 09_create_gateway_role.py
│   │   ├── 10_create_lambda.py
│   │   ├── 11_create_gateway.py
│   │   ├── 12_add_lambda_to_gateway.py
│   │   ├── 13_list_gateway_targets.py
│   │   └── 16_create_runtime_role.py
│   ├── tests/               # Test scripts
│   │   ├── 02_test_agent.py
│   │   ├── 05_test_memory.py
│   │   ├── 07_test_memory_agent.py
│   │   └── 15_test_full_agent.py
│   └── ui/                  # User interface
│       ├── streamlit_app.py
│       └── run_streamlit.sh
├── scripts/                 # Deployment & operations
│   ├── 19_deploy_agent.py
│   ├── 20_check_status.py
│   ├── 21_invoke_agent.py
│   ├── 22_get_dashboard.py
│   └── 23_get_logs_info.py
├── docs/                    # Documentation
├── agentcore-mcp-server/    # MCP server implementation
├── requirements.txt
├── requirements_streamlit.txt
├── LICENSE
└── README.md
```

## 🔧 Custom Tools

The agent includes three custom business logic tools:

1. **check_return_eligibility** - Validates return eligibility based on purchase date and category
2. **calculate_refund_amount** - Calculates refund based on price, condition, and return reason
3. **format_policy_response** - Formats policy information in a customer-friendly way

## 📊 Monitoring & Observability

### CloudWatch Dashboard
```bash
python3 scripts/22_get_dashboard.py
```

### View Logs
```bash
python3 scripts/23_get_logs_info.py
```

### Real-time Log Tailing
```bash
aws logs tail /aws/bedrock-agentcore/runtimes/returns_refunds_agent-* --follow
```

## 🧪 Testing

### Local Testing
```bash
# Test original agent
python3 src/tests/02_test_agent.py

# Test memory integration
python3 src/tests/07_test_memory_agent.py

# Test full agent with all features
python3 src/tests/15_test_full_agent.py
```

### Production Testing
```bash
# Invoke deployed agent
python3 scripts/21_invoke_agent.py
```

## 🔐 Security

- OAuth 2.0 authentication via Cognito
- IAM roles with least-privilege permissions
- Secure credential management via environment variables
- Configuration files excluded from version control

## 📈 Features

- ✅ **Memory** - Persistent conversation history and preferences
- ✅ **Gateway** - External API integration via Lambda
- ✅ **Knowledge Base** - Document retrieval for policies
- ✅ **Custom Tools** - Business logic implementation
- ✅ **Streaming** - Real-time response streaming
- ✅ **Authentication** - OAuth 2.0 with Cognito
- ✅ **Observability** - CloudWatch Logs, X-Ray traces
- ✅ **Auto-scaling** - Serverless with automatic scaling
- ✅ **Error Handling** - Comprehensive error handling and logging

## 📚 Documentation

- [AgentCore Documentation](https://aws.github.io/bedrock-agentcore-starter-toolkit/)
- [Strands Agents Documentation](https://strandsagents.com/)
- [Amazon Bedrock Documentation](https://docs.aws.amazon.com/bedrock/)

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Built with [Amazon Bedrock AgentCore](https://aws.amazon.com/bedrock/)
- Powered by [Strands Agents Framework](https://strandsagents.com/)
- UI built with [Streamlit](https://streamlit.io/)

## 📧 Contact

For questions or support, please open an issue on GitHub.

---

**Built with ❤️ using Amazon Bedrock AgentCore Runtime**
