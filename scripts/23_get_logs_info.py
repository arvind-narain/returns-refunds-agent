#!/usr/bin/env python3
"""
Script to get CloudWatch log group information for agent logs.

Provides log group details and AWS CLI commands for viewing logs.
"""

import json
import os
from datetime import datetime

print("=" * 80)
print("CLOUDWATCH LOGS INFORMATION")
print("=" * 80)

# Check if runtime config exists
if not os.path.exists('runtime_config.json'):
    print("\n❌ Error: runtime_config.json not found")
    print("Please run 19_deploy_agent.py first")
    exit(1)

# Load configuration
with open('runtime_config.json') as f:
    runtime_config = json.load(f)

agent_arn = runtime_config["agent_arn"]
agent_name = runtime_config["agent_name"]
region = runtime_config["region"]

# Extract agent ID from ARN
agent_id = agent_arn.split('/')[-1]

# Build log group name
log_group = f"/aws/bedrock-agentcore/runtimes/{agent_id}-DEFAULT"

# Get current date for log stream prefix
current_date = datetime.now().strftime("%Y/%m/%d")

print(f"\n📊 Agent Information:")
print(f"   Agent Name: {agent_name}")
print(f"   Agent ARN: {agent_arn}")
print(f"   Agent ID: {agent_id}")
print(f"   Region: {region}")

print(f"\n📝 Log Group:")
print(f"   {log_group}")

print(f"\n🔍 Log Streams:")
print(f"   Runtime Logs: {current_date}/[runtime-logs]*")
print(f"   OpenTelemetry: otel-rt-logs")

print(f"\n💻 AWS CLI Commands:")

# Tail logs (real-time)
tail_command = f'aws logs tail {log_group} --log-stream-name-prefix "{current_date}/[runtime-logs]" --follow'
print(f"\n1. Tail logs (real-time):")
print(f"   {tail_command}")

# Recent logs
recent_command = f'aws logs tail {log_group} --log-stream-name-prefix "{current_date}/[runtime-logs]" --since 1h'
print(f"\n2. View recent logs (last hour):")
print(f"   {recent_command}")

# Last 10 minutes
recent_10m_command = f'aws logs tail {log_group} --log-stream-name-prefix "{current_date}/[runtime-logs]" --since 10m'
print(f"\n3. View last 10 minutes:")
print(f"   {recent_10m_command}")

# Filter logs
filter_command = f'aws logs tail {log_group} --log-stream-name-prefix "{current_date}/[runtime-logs]" --filter-pattern "ERROR"'
print(f"\n4. Filter for errors:")
print(f"   {filter_command}")

# OpenTelemetry logs
otel_command = f'aws logs tail {log_group} --log-stream-names "otel-rt-logs" --follow'
print(f"\n5. View OpenTelemetry logs:")
print(f"   {otel_command}")

print(f"\n🌐 CloudWatch Console:")
console_url = f"https://console.aws.amazon.com/cloudwatch/home?region={region}#logsV2:log-groups/log-group/{log_group.replace('/', '$252F')}"
print(f"   {console_url}")

print(f"\n📈 Common Log Patterns:")
print("   • Agent invocations: Look for 'Agent Invocation Started'")
print("   • Tool calls: Search for 'Tool #' or tool names")
print("   • Memory access: Filter for 'memory' or 'retrieve'")
print("   • Gateway calls: Look for 'Gateway' or 'MCP'")
print("   • Errors: Filter for 'ERROR' or 'Exception'")

print(f"\n💡 Tips:")
print("   • Use --follow for real-time monitoring")
print("   • Use --since to limit time range (e.g., 1h, 30m, 1d)")
print("   • Use --filter-pattern to search for specific text")
print("   • Combine with grep for advanced filtering:")
print(f"     {tail_command} | grep 'user_001'")

print("\n" + "=" * 80)
print("📋 Log group information ready!")
print("=" * 80)
