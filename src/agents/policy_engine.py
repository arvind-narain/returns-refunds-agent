"""
Policy Engine: Load and evaluate configurable return policies

This module replaces hardcoded business rules with configurable policies
loaded from YAML/JSON files.
"""

import os
import json
import yaml
import logging
from datetime import datetime
from typing import Dict, Any, Optional
from pathlib import Path

logger = logging.getLogger(__name__)


class PolicyEngine:
    """Load and evaluate return policies from configuration files"""
    
    def __init__(self, policy_file: Optional[str] = None):
        """
        Initialize policy engine with a policy file.
        
        Args:
            policy_file: Path to policy YAML/JSON file. 
                        If None, uses POLICY_FILE env var or default policy.
        """
        if policy_file is None:
            policy_file = os.environ.get('POLICY_FILE', 'policies/default_policy.yaml')
        
        self.policy_file = policy_file
        self.policy = self._load_policy()
        self._validate_policy()
        
        logger.info(f"Loaded policy: {self.policy['policy_name']} v{self.policy['version']}")
    
    def _load_policy(self) -> Dict[str, Any]:
        """Load policy from YAML or JSON file"""
        try:
            policy_path = Path(self.policy_file)
            
            if not policy_path.exists():
                logger.error(f"Policy file not found: {self.policy_file}")
                raise FileNotFoundError(f"Policy file not found: {self.policy_file}")
            
            with open(policy_path, 'r') as f:
                if policy_path.suffix in ['.yaml', '.yml']:
                    policy = yaml.safe_load(f)
                elif policy_path.suffix == '.json':
                    policy = json.load(f)
                else:
                    raise ValueError(f"Unsupported file format: {policy_path.suffix}")
            
            return policy
        
        except Exception as e:
            logger.error(f"Failed to load policy: {e}")
            raise
    
    def _validate_policy(self):
        """Validate policy has required fields"""
        required_fields = ['policy_id', 'policy_name', 'version', 'return_windows', 'refund_rules']
        
        for field in required_fields:
            if field not in self.policy:
                raise ValueError(f"Policy missing required field: {field}")
        
        # Validate return_windows has default
        if 'default' not in self.policy['return_windows']:
            raise ValueError("Policy return_windows must include 'default'")
    
    def get_return_window(self, category: str) -> int:
        """
        Get return window in days for a category.
        
        Args:
            category: Item category (e.g., 'electronics', 'clothing')
        
        Returns:
            Number of days for return window
        """
        category_lower = category.lower()
        return_windows = self.policy['return_windows']
        
        return return_windows.get(category_lower, return_windows['default'])
    
    def is_returnable_category(self, category: str) -> bool:
        """
        Check if category is returnable.
        
        Args:
            category: Item category
        
        Returns:
            True if category can be returned, False otherwise
        """
        non_returnable = self.policy.get('non_returnable_categories', [])
        return category.lower() not in [c.lower() for c in non_returnable]
    
    def check_eligibility(self, purchase_date: str, category: str) -> Dict[str, Any]:
        """
        Check if item is eligible for return.
        
        Args:
            purchase_date: Purchase date in YYYY-MM-DD format
            category: Item category
        
        Returns:
            Dict with eligibility status and details
        """
        try:
            purchase_dt = datetime.strptime(purchase_date, '%Y-%m-%d')
            days_since_purchase = (datetime.now() - purchase_dt).days
            
            # Check if category is returnable
            if not self.is_returnable_category(category):
                return {
                    'eligible': False,
                    'reason': f'{category} items are not eligible for return',
                    'days_since_purchase': days_since_purchase,
                    'policy_version': self.policy['version']
                }
            
            # Check return window
            window = self.get_return_window(category)
            
            if days_since_purchase <= window:
                return {
                    'eligible': True,
                    'reason': f'Item is within {window}-day return window',
                    'days_since_purchase': days_since_purchase,
                    'days_remaining': window - days_since_purchase,
                    'policy_version': self.policy['version']
                }
            else:
                return {
                    'eligible': False,
                    'reason': f'Return window of {window} days has expired',
                    'days_since_purchase': days_since_purchase,
                    'policy_version': self.policy['version']
                }
        
        except ValueError as e:
            logger.error(f"Date parsing error: {e}")
            return {
                'eligible': False,
                'reason': 'Invalid date format. Please use YYYY-MM-DD',
                'policy_version': self.policy['version']
            }
    
    def calculate_refund(self, original_price: float, condition: str, reason: str) -> Dict[str, Any]:
        """
        Calculate refund amount based on policy rules.
        
        Args:
            original_price: Original purchase price
            condition: Item condition (unopened, opened_unused, used, damaged)
            reason: Return reason (defective, wrong_item, changed_mind)
        
        Returns:
            Dict with refund calculation details
        """
        condition_lower = condition.lower()
        reason_lower = reason.lower()
        
        refund_rules = self.policy['refund_rules']
        
        # Get rule for this reason
        if reason_lower in ['defective', 'wrong_item']:
            rule = refund_rules.get(reason_lower, refund_rules.get('defective'))
        else:
            # For changed_mind, get rule by condition
            changed_mind_rules = refund_rules.get('changed_mind', {})
            rule = changed_mind_rules.get(condition_lower, {
                'refund_percentage': 100,
                'restocking_fee_percentage': 0,
                'shipping_refunded': False
            })
        
        # Calculate refund
        refund_percentage = rule.get('refund_percentage', 100)
        restocking_fee_pct = rule.get('restocking_fee_percentage', 0)
        shipping_refunded = rule.get('shipping_refunded', False)
        
        refund_amount = (original_price * refund_percentage / 100)
        restocking_fee = original_price * restocking_fee_pct / 100
        refund_amount -= restocking_fee
        refund_amount = max(0, refund_amount)  # Ensure non-negative
        
        return {
            'original_price': original_price,
            'refund_amount': round(refund_amount, 2),
            'refund_percentage': refund_percentage,
            'restocking_fee': round(restocking_fee, 2),
            'shipping_refunded': shipping_refunded,
            'item_condition': condition,
            'return_reason': reason,
            'policy_version': self.policy['version']
        }
    
    def get_policy_info(self) -> Dict[str, Any]:
        """Get policy metadata"""
        return {
            'policy_id': self.policy['policy_id'],
            'policy_name': self.policy['policy_name'],
            'version': self.policy['version'],
            'effective_date': self.policy.get('effective_date', 'N/A')
        }


# Global policy engine instance (lazy loaded)
_policy_engine: Optional[PolicyEngine] = None


def get_policy_engine() -> PolicyEngine:
    """Get or create global policy engine instance"""
    global _policy_engine
    if _policy_engine is None:
        _policy_engine = PolicyEngine()
    return _policy_engine
