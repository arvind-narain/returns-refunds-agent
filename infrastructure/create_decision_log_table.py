#!/usr/bin/env python3
"""
Create DynamoDB table for decision logging

Usage:
    python infrastructure/create_decision_log_table.py

Note: If this fails due to permissions, decision logging will automatically
fall back to S3 storage.
"""

import json
import boto3
from botocore.exceptions import ClientError

def create_decision_log_table():
    """Create DynamoDB table for decision logs"""
    
    # Load table schema
    with open('infrastructure/decision_log_table.json', 'r') as f:
        table_config = json.load(f)
    
    dynamodb = boto3.client('dynamodb', region_name='us-west-2')
    
    try:
        # Check if table already exists
        try:
            dynamodb.describe_table(TableName=table_config['TableName'])
            print(f"✓ Table {table_config['TableName']} already exists")
            return
        except ClientError as e:
            if e.response['Error']['Code'] != 'ResourceNotFoundException':
                raise
        
        # Create table
        print(f"Creating DynamoDB table: {table_config['TableName']}...")
        response = dynamodb.create_table(**table_config)
        
        # Wait for table to be created
        print("Waiting for table to be active...")
        waiter = dynamodb.get_waiter('table_exists')
        waiter.wait(TableName=table_config['TableName'])
        
        print(f"✓ Table {table_config['TableName']} created successfully")
        print(f"  ARN: {response['TableDescription']['TableArn']}")
        
    except ClientError as e:
        print(f"✗ Failed to create table: {e}")
        print("  Decision logging will fall back to S3 storage")
        raise

if __name__ == "__main__":
    create_decision_log_table()
