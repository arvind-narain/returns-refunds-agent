# Returns & Refunds Agent - AgentCore Runtime

A production-ready AI agent for handling customer returns and refunds, built with Amazon Bedrock AgentCore Runtime.

## 🎯 Overview

This project demonstrates a complete end-to-end implementation of an AI agent with:

- **Memory Integration** - Remembers customer preferences and conversation history
- **Gateway Integration** - Connects to external APIs (Lambda functions) for order lookup
- **Knowledge Base** - Retrieves Amazon return policy documents
- **Custom Tools** - Business logic for eligibility checks and refund calculations
- **Production Deployment** - Serverless deployment on AgentCore Runtime
- **Observability** - CloudWatch Logs, X-Ray traces, and GenAI dashboards

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

### 3. Deploy the Agent

Follow the numbered scripts in order:

```bash
# Step 1: Create Memory
python3 03_create_memory.py

# Step 2: Seed Memory with sample data
python3 04_seed_memory.py

# Step 3: Create Cognito for authentication
python3 08_create_cognito.py

# Step 4: Create IAM roles
python3 09_create_gateway_role.py
python3 16_create_runtime_role.py

# Step 5: Create Lambda function
python3 10_create_lambda.py

# Step 6: Create Gateway
python3 11_create_gateway.py
python3 12_add_lambda_to_gateway.py

# Step 7: Deploy to Runtime
python3 19_deploy_agent.py

# Step 8: Check status
python3 20_check_status.py

# Step 9: Test the agent
python3 21_invoke_agent.py
```

## 📁 Project Structure

```
.
├── 01_returns_refunds_agent.py      # Original agent with KB
├── 03_create_memory.py              # Create AgentCore Memory
├── 04_seed_memory.py                # Seed memory with sample data
├── 05_test_memory.py                # Test memory retrieval
├── 06_memory_enabled_agent.py       # Agent with memory
├── 08_create_cognito.py             # Create Cognito user pool
├── 09_create_gateway_role.py        # Create IAM role for gateway
├── 10_create_lambda.py              # Create Lambda function
├── 11_create_gateway.py             # Create AgentCore Gateway
├── 12_add_lambda_to_gateway.py      # Add Lambda to gateway
├── 13_list_gateway_targets.py       # List gateway targets
├── 14_full_agent.py                 # Full-featured agent (local)
├── 15_test_full_agent.py            # Test full agent locally
├── 16_create_runtime_role.py        # Create runtime execution role
├── 17_runtime_agent.py              # Production runtime agent
├── 19_deploy_agent.py               # Deploy to AgentCore Runtime
├── 20_check_status.py               # Check deployment status
├── 21_invoke_agent.py               # Invoke deployed agent
├── 22_get_dashboard.py              # Get observability dashboard
├── 23_get_logs_info.py              # Get CloudWatch logs info
├── streamlit_app.py                 # Streamlit chat interface
├── requirements.txt                 # Python dependencies
└── README.md                        # This file
```

## 🎨 Streamlit Chat Interface

Launch the web interface:

```bash
./run_streamlit.sh
```

Or manually:

```bash
pip install -r requirements_streamlit.txt
streamlit run streamlit_app.py
```

Access at: http://localhost:8501

## 🔧 Custom Tools

The agent includes three custom tools:

1. **check_return_eligibility** - Validates if items can be returned based on purchase date and category
2. **calculate_refund_amount** - Calculates refund based on price, condition, and return reason
3. **format_policy_response** - Formats policy information in a customer-friendly way

## 📊 Monitoring & Observability

### CloudWatch Dashboard
```bash
python3 22_get_dashboard.py
```

### View Logs
```bash
python3 23_get_logs_info.py
```

### Real-time Log Tailing
```bash
aws logs tail /aws/bedrock-agentcore/runtimes/returns_refunds_agent-* --follow
```

## 🧪 Testing

### Local Testing
```bash
# Test original agent
python3 02_test_agent.py

# Test memory integration
python3 07_test_memory_agent.py

# Test full agent with all features
python3 15_test_full_agent.py
```

### Production Testing
```bash
# Invoke deployed agent
python3 21_invoke_agent.py
```

## 🔐 Security

- OAuth 2.0 authentication via Cognito
- IAM roles with least-privilege permissions
- Secure credential management via environment variables
- VPC support for private resources (optional)

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

## 🛠️ Configuration

Configuration files are generated during deployment and stored as JSON:

- `memory_config.json` - Memory resource ID
- `cognito_config.json` - Cognito credentials
- `gateway_config.json` - Gateway URL and ID
- `lambda_config.json` - Lambda function ARN
- `runtime_config.json` - Deployed agent ARN

**Note:** These files contain sensitive information and are excluded from Git.

## 📚 Documentation

- [AgentCore Documentation](https://aws.github.io/bedrock-agentcore-starter-toolkit/)
- [Strands Agents Documentation](https://strandsagents.com/)
- [Amazon Bedrock Documentation](https://docs.aws.amazon.com/bedrock/)

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- Built with [Amazon Bedrock AgentCore](https://aws.amazon.com/bedrock/)
- Powered by [Strands Agents Framework](https://strandsagents.com/)
- UI built with [Streamlit](https://streamlit.io/)

## 📧 Contact

For questions or support, please open an issue on GitHub.

---

**Built with ❤️ using Amazon Bedrock AgentCore Runtime**
