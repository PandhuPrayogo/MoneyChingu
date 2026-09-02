import plotly.graph_objects as go
import plotly.express as px
from typing import Dict, Any, List
import pandas as pd

def create_category_pie_chart(category_breakdown: Dict[str, float], currency: str = "USD") -> go.Figure:
    """Render sleek Donut Chart of Spending by Category."""
    if not category_breakdown:
        fig = go.Figure()
        fig.add_annotation(
            text="No expenses recorded for this period yet 💸",
            showarrow=False,
            font=dict(size=14, color="#94a3b8")
        )
        fig.update_layout(
            template="plotly_dark",
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            height=300,
            margin=dict(l=20, r=20, t=30, b=20)
        )
        return fig

    labels = list(category_breakdown.keys())
    values = list(category_breakdown.values())

    fig = go.Figure(data=[go.Pie(
        labels=labels,
        values=values,
        hole=0.55,
        textinfo="label+percent",
        insidetextorientation="radial",
        marker=dict(colors=px.colors.qualitative.Prism),
        hovertemplate="<b>%{label}</b><br>Amount: %{value:,.2f} " + currency + "<br>Share: %{percent}<extra></extra>"
    )])

    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5),
        height=320,
        margin=dict(l=20, r=20, t=20, b=20)
    )
    return fig

def create_cash_flow_bar_chart(income: float, expense: float, net_savings: float, currency: str = "USD") -> go.Figure:
    """Render comparative Bar Chart for Cash Flow."""
    categories = ["Income", "Expenses", "Net Savings"]
    amounts = [income, expense, net_savings]
    colors = ["#10b981", "#ffffff", "#6366f1" if net_savings >= 0 else "#f59e0b"]

    fig = go.Figure(data=[
        go.Bar(
            x=categories,
            y=amounts,
            marker_color=colors,
            text=[f"{v:,.2f} {currency}" for v in amounts],
            textposition="auto",
            hovertemplate="<b>%{x}</b>: %{y:,.2f} " + currency + "<extra></extra>"
        )
    ])

    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        height=300,
        margin=dict(l=20, r=20, t=30, b=20),
        yaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.05)")
    )
    return fig

def create_budget_progress_chart(budgets_data: List[Dict[str, Any]], currency: str = "USD") -> go.Figure:
    """Render horizontal comparison bar chart for Category Budgets vs Actual Spending."""
    if not budgets_data:
        fig = go.Figure()
        fig.add_annotation(
            text="No active category budgets configured.",
            showarrow=False,
            font=dict(size=14, color="#94a3b8")
        )
        fig.update_layout(
            template="plotly_dark",
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            height=250
        )
        return fig

    cats = [b["category"] for b in budgets_data]
    spent = [b["spent"] for b in budgets_data]
    limits = [b["monthly_limit"] for b in budgets_data]

    fig = go.Figure()
    # Budget Limit Bar (Background)
    fig.add_trace(go.Bar(
        y=cats,
        x=limits,
        name="Budget Limit",
        orientation="h",
        marker=dict(color="rgba(99, 102, 241, 0.25)", line=dict(color="#6366f1", width=1.5)),
        hovertemplate="Limit: %{x:,.2f} " + currency + "<extra></extra>"
    ))

    # Actual Spent Bar
    fig.add_trace(go.Bar(
        y=cats,
        x=spent,
        name="Actual Spent",
        orientation="h",
        marker=dict(color=["#ffffff" if s > l else "#10b981" for s, l in zip(spent, limits)]),
        hovertemplate="Spent: %{x:,.2f} " + currency + "<extra></extra>"
    ))

    fig.update_layout(
        barmode="overlay",
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        height=max(250, len(cats) * 55),
        margin=dict(l=20, r=20, t=30, b=20),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    return fig
