from typing import Dict, Any, List, Optional
from datetime import datetime

from skills.base import BaseSkill
from database.db import db
from config import USD_TO_IDR_RATE

class FinancialAnalyticsSkill(BaseSkill):
    """
    Financial Analytics & Budgeting Skill:
    Computes cash flow summaries, budget burn-rates, currency conversions,
    and identifies financial anomalies.
    """
    name = "financial_analytics"
    description = "Analyzes monthly cash flows, category spending velocity, budget limits, and currency conversions."
    parameters = {
        "type": "object",
        "properties": {
            "analysis_type": {
                "type": "string",
                "enum": ["monthly_summary", "budget_status", "net_worth", "convert_currency", "spending_insights"],
                "description": "The financial analysis operation to run"
            },
            "month_year": {"type": "string", "description": "Target month in YYYY-MM format"},
            "currency": {"type": "string", "enum": ["USD", "IDR"], "description": "Target reporting currency"},
            "amount": {"type": "number", "description": "Amount to convert (if convert_currency)"},
            "from_currency": {"type": "string", "enum": ["USD", "IDR"]},
            "to_currency": {"type": "string", "enum": ["USD", "IDR"]}
        },
        "required": ["analysis_type"]
    }

    def execute(self, **kwargs) -> Dict[str, Any]:
        analysis_type = kwargs.get("analysis_type")
        currency = (kwargs.get("currency") or "USD").upper()
        month_year = kwargs.get("month_year") or datetime.now().strftime("%Y-%m")

        if analysis_type == "monthly_summary":
            return self._get_monthly_summary(month_year, currency)
        elif analysis_type == "budget_status":
            return self._get_budget_status(month_year, currency)
        elif analysis_type == "net_worth":
            return self._get_net_worth(currency)
        elif analysis_type == "convert_currency":
            return self._convert_currency(kwargs)
        elif analysis_type == "spending_insights":
            return self._get_spending_insights(month_year, currency)
        else:
            return {"status": "error", "message": f"Unknown analysis type: {analysis_type}"}

    def _get_monthly_summary(self, month_year: str, currency: str) -> Dict[str, Any]:
        summary = db.get_monthly_summary(month_year, display_currency=currency)
        return {
            "status": "success",
            "summary": summary
        }

    def _get_budget_status(self, month_year: str, currency: str) -> Dict[str, Any]:
        budgets = db.get_budgets(month_year)
        summary = db.get_monthly_summary(month_year, display_currency=currency)
        spending_by_cat = summary.get("category_breakdown", {})

        budget_reports = []
        overspent_categories = []

        for b in budgets:
            cat = b["category"]
            limit = b["monthly_limit"]
            b_curr = b["currency"]

            # Convert limit to requested currency if needed
            conv_limit = limit
            if currency == "USD" and b_curr == "IDR":
                conv_limit = limit / USD_TO_IDR_RATE
            elif currency == "IDR" and b_curr == "USD":
                conv_limit = limit * USD_TO_IDR_RATE

            spent = spending_by_cat.get(cat, 0.0)
            remaining = conv_limit - spent
            burn_rate_pct = round((spent / conv_limit * 100), 1) if conv_limit > 0 else 0.0

            if spent > conv_limit:
                overspent_categories.append({
                    "category": cat,
                    "spent": spent,
                    "limit": conv_limit,
                    "over_by": spent - conv_limit
                })

            budget_reports.append({
                "category": cat,
                "monthly_limit": round(conv_limit, 2),
                "spent": round(spent, 2),
                "remaining": round(remaining, 2),
                "burn_rate_pct": burn_rate_pct,
                "currency": currency,
                "is_overspent": spent > conv_limit
            })

        return {
            "status": "success",
            "month_year": month_year,
            "currency": currency,
            "budgets": budget_reports,
            "has_overspending": len(overspent_categories) > 0,
            "overspent_alerts": overspent_categories
        }

    def _get_net_worth(self, currency: str) -> Dict[str, Any]:
        net_worth_data = db.get_total_balance_summary(display_currency=currency)
        return {
            "status": "success",
            "net_worth": net_worth_data
        }

    def _convert_currency(self, params: Dict[str, Any]) -> Dict[str, Any]:
        amount = float(params.get("amount", 0.0))
        from_curr = (params.get("from_currency") or "USD").upper()
        to_curr = (params.get("to_currency") or "IDR").upper()

        if from_curr == to_curr:
            converted = amount
        elif from_curr == "USD" and to_curr == "IDR":
            converted = amount * USD_TO_IDR_RATE
        elif from_curr == "IDR" and to_curr == "USD":
            converted = amount / USD_TO_IDR_RATE
        else:
            return {"status": "error", "message": f"Unsupported conversion from {from_curr} to {to_curr}"}

        return {
            "status": "success",
            "original_amount": amount,
            "from_currency": from_curr,
            "to_currency": to_curr,
            "converted_amount": round(converted, 2),
            "rate_used": USD_TO_IDR_RATE
        }

    def _get_spending_insights(self, month_year: str, currency: str) -> Dict[str, Any]:
        txs = db.get_transactions(limit=100, month=month_year)
        expenses = [t for t in txs if t["type"] == "expense"]
        
        # Sort by amount descending
        expenses.sort(key=lambda x: x["amount"], reverse=True)
        top_expenses = expenses[:3]
        
        return {
            "status": "success",
            "top_3_expenses": top_expenses,
            "total_transactions_count": len(txs)
        }

financial_analytics_skill = FinancialAnalyticsSkill()
