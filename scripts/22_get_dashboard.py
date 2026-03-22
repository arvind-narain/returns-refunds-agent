#!/usr/bin/env python3
"""
Script to get CloudWatch GenAI Observability dashboard URL.

Provides access to monitoring and observability for the deployed agent.
"""

import json
import os

print("=" * 80)
print("CLOUDWATCH GENAI OBSERVABILITY DASHBOARD")
print("=" * 80)

# Load runtime config if available
agent_arn = None
agent_name = None

if os.path.exists('runtime_config.json'):
    with open('runtime_config.json') as f:
        runtime_config = json.load(f)
        agent_arn = runtime_config.get('agent_arn')
        agent_name = runtime_config.get('agent_name')
    
    print(f"\n📊 Agent Information:")
    print(f"   Agent Name: {agent_name}")
    print(f"   Agent ARN: {agent_arn}")
    print(f"   Region: {runtime_config.get('region', 'us-west-2')}")

# Build dashboard URL
region = "us-west-2"
dashboard_url = f"https://console.aws.amazon.com/cloudwatch/home?region={region}#gen-ai-observability/agent-core"

print(f"\n🔗 Dashboard URL:")
print(f"   {dashboard_url}")

print(f"\n✨ Dashboard Features:")
print("   • Agent performance metrics (latency, throughput)")
print("   • Request traces and spans (X-Ray integration)")
print("   • Session history and conversation flows")
print("   • Error rates and failure patterns")
print("   • Tool invocation details and timing")
print("   • Memory retrieval statistics")
print("   • Gateway call monitoring")

print(f"\n📈 What You Can Monitor:")
print("   1. Request Volume - Track agent invocations over time")
print("   2. Response Times - Monitor latency and performance")
print("   3. Success Rates - Identify errors and failures")
print("   4. Tool Usage - See which tools are being called")
print("   5. Memory Access - Track memory retrieval patterns")
print("   6. Gateway Calls - Monitor external API integrations")

print(f"\n🔍 Additional Monitoring:")

# Log group information
if agent_name:
    log_group_name = f"/aws/bedrock-agentcore/runtimes/{agent_name.replace('_', '-')}-*"
    print(f"\n   CloudWatch Logs:")
    print(f"   Log Group: {log_group_name}")
    print(f"\n   View logs with:")
    print(f"   aws logs tail {log_group_name} --follow")
    print(f"\n   View recent logs:")
    print(f"   aws logs tail {log_group_name} --since 1h")

print(f"\n📊 X-Ray Traces:")
print(f"   https://console.aws.amazon.com/xray/home?region={region}#/traces")

print(f"\n💡 Tips:")
print("   • Use the dashboard to identify performance bottlenecks")
print("   • Set up CloudWatch alarms for error rates")
print("   • Monitor memory retrieval patterns for optimization")
print("   • Track gateway call latencies")
print("   • Use X-Ray traces for detailed request analysis")

print("\n" + "=" * 80)
print("🌐 Open the dashboard URL in your browser to start monitoring!")
print("=" * 80)
