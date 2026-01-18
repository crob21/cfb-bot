#!/usr/bin/env python3
"""
Cost tracking and alert system
"""

import logging
import os
from datetime import datetime
from typing import Dict, Optional

from .storage import get_storage

logger = logging.getLogger('CFB26Bot.CostTracker')


class CostTracker:
    """Track costs and send alerts when thresholds are exceeded"""

    def __init__(self):
        self._storage = get_storage()
        self._alert_channel_id = int(os.getenv('ADMIN_CHANNEL_ID', 0)) if os.getenv('ADMIN_CHANNEL_ID') else None

        # Monthly budget thresholds (in USD)
        self.monthly_budget = {
            'ai': float(os.getenv('AI_MONTHLY_BUDGET', 10.0)),
            'zyte': float(os.getenv('ZYTE_MONTHLY_BUDGET', 5.0)),
            'total': float(os.getenv('TOTAL_MONTHLY_BUDGET', 15.0))
        }

        # Alert thresholds (percentage of budget)
        self.alert_thresholds = [0.5, 0.8, 0.9, 1.0]  # 50%, 80%, 90%, 100%

        self._alerts_sent = {}  # Track which alerts have been sent

    async def get_monthly_costs(self) -> Dict[str, float]:
        """Get costs for current month"""
        current_month = datetime.now().strftime('%Y-%m')

        # Load from storage
        data = await self._storage.load("cost_tracker", current_month)

        if data:
            return {
                'ai': data.get('ai_cost', 0.0),
                'zyte': data.get('zyte_cost', 0.0),
                'total': data.get('ai_cost', 0.0) + data.get('zyte_cost', 0.0)
            }

        return {'ai': 0.0, 'zyte': 0.0, 'total': 0.0}

    async def record_cost(self, service: str, amount: float):
        """Record a cost and check if alerts should be sent

        Args:
            service: 'ai' or 'zyte'
            amount: Cost in USD
        """
        current_month = datetime.now().strftime('%Y-%m')

        # Load current month's data
        data = await self._storage.load("cost_tracker", current_month) or {}

        # Update costs
        current_ai = data.get('ai_cost', 0.0)
        current_zyte = data.get('zyte_cost', 0.0)

        if service == 'ai':
            current_ai += amount
        elif service == 'zyte':
            current_zyte += amount

        data['ai_cost'] = current_ai
        data['zyte_cost'] = current_zyte
        data['total_cost'] = current_ai + current_zyte
        data['last_updated'] = datetime.now().isoformat()

        # Save updated data
        await self._storage.save("cost_tracker", current_month, data)

        logger.debug(f"💰 Recorded ${amount:.4f} for {service} (total this month: ${data['total_cost']:.4f})")

        # Check if alerts should be sent
        await self._check_alerts(current_ai, current_zyte, current_ai + current_zyte)

    async def _check_alerts(self, ai_cost: float, zyte_cost: float, total_cost: float):
        """Check if any cost thresholds have been crossed"""
        current_month = datetime.now().strftime('%Y-%m')
        alert_key = f"{current_month}_alerts"

        # Load alerts already sent this month
        alerts_data = await self._storage.load("cost_alerts", alert_key) or {}

        alerts_to_send = []

        # Check AI budget
        for threshold in self.alert_thresholds:
            threshold_amount = self.monthly_budget['ai'] * threshold
            alert_id = f"ai_{int(threshold * 100)}"

            if ai_cost >= threshold_amount and alert_id not in alerts_data:
                alerts_to_send.append({
                    'service': 'AI (OpenAI/Anthropic)',
                    'threshold': int(threshold * 100),
                    'current': ai_cost,
                    'budget': self.monthly_budget['ai']
                })
                alerts_data[alert_id] = datetime.now().isoformat()

        # Check Zyte budget
        for threshold in self.alert_thresholds:
            threshold_amount = self.monthly_budget['zyte'] * threshold
            alert_id = f"zyte_{int(threshold * 100)}"

            if zyte_cost >= threshold_amount and alert_id not in alerts_data:
                alerts_to_send.append({
                    'service': 'Zyte API',
                    'threshold': int(threshold * 100),
                    'current': zyte_cost,
                    'budget': self.monthly_budget['zyte']
                })
                alerts_data[alert_id] = datetime.now().isoformat()

        # Check total budget
        for threshold in self.alert_thresholds:
            threshold_amount = self.monthly_budget['total'] * threshold
            alert_id = f"total_{int(threshold * 100)}"

            if total_cost >= threshold_amount and alert_id not in alerts_data:
                alerts_to_send.append({
                    'service': 'Total (All Services)',
                    'threshold': int(threshold * 100),
                    'current': total_cost,
                    'budget': self.monthly_budget['total']
                })
                alerts_data[alert_id] = datetime.now().isoformat()

        # Send alerts
        if alerts_to_send:
            await self._send_alerts(alerts_to_send)
            # Save updated alerts
            await self._storage.save("cost_alerts", alert_key, alerts_data)

    async def _send_alerts(self, alerts):
        """Send cost alert notifications"""
        for alert in alerts:
            emoji = "⚠️" if alert['threshold'] < 100 else "🚨"
            percent = (alert['current'] / alert['budget'] * 100) if alert['budget'] > 0 else 0

            logger.warning(
                f"{emoji} COST ALERT: {alert['service']} at {alert['threshold']}% of budget "
                f"(${alert['current']:.2f} / ${alert['budget']:.2f})"
            )

            # TODO: Send Discord DM or channel message to admin
            # This would require bot instance access, so for now just log

    async def get_budget_status(self) -> Dict:
        """Get current budget status for display"""
        costs = await self.get_monthly_costs()

        return {
            'costs': costs,
            'budgets': self.monthly_budget,
            'percentages': {
                'ai': (costs['ai'] / self.monthly_budget['ai'] * 100) if self.monthly_budget['ai'] > 0 else 0,
                'zyte': (costs['zyte'] / self.monthly_budget['zyte'] * 100) if self.monthly_budget['zyte'] > 0 else 0,
                'total': (costs['total'] / self.monthly_budget['total'] * 100) if self.monthly_budget['total'] > 0 else 0
            },
            'remaining': {
                'ai': max(0, self.monthly_budget['ai'] - costs['ai']),
                'zyte': max(0, self.monthly_budget['zyte'] - costs['zyte']),
                'total': max(0, self.monthly_budget['total'] - costs['total'])
            }
        }


# Global instance
_cost_tracker: Optional[CostTracker] = None


def get_cost_tracker() -> CostTracker:
    """Get the global cost tracker instance"""
    global _cost_tracker

    if _cost_tracker is None:
        _cost_tracker = CostTracker()
        logger.info("💰 Cost tracker initialized")

    return _cost_tracker

