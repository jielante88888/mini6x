"""
Report template management system
Handles customizable templates for different report types
"""

from typing import Dict, Any, Optional
from dataclasses import dataclass
from pathlib import Path


@dataclass
class ReportTemplate:
    """Report template configuration"""
    template_id: str
    name: str
    description: str
    report_type: str
    sections: Dict[str, Any]
    styling: Dict[str, Any]
    custom_fields: Optional[Dict[str, str]] = None


class ReportTemplateManager:
    """Manages report templates for different formats and types"""
    
    def __init__(self):
        self.templates = self._load_default_templates()
    
    def _load_default_templates(self) -> Dict[str, ReportTemplate]:
        """Load default report templates"""
        return {
            "account_summary_default": ReportTemplate(
                template_id="account_summary_default",
                name="Account Summary (Default)",
                description="Comprehensive account summary with balance overview and performance",
                report_type="ACCOUNT_SUMMARY",
                sections={
                    "header": {
                        "title": "Account Summary Report",
                        "subtitle": "Portfolio Overview and Performance Analysis",
                        "include_logo": True,
                        "company_name": "Crypto Trading Terminal"
                    },
                    "summary": {
                        "total_portfolio_value": True,
                        "total_daily_change": True,
                        "top_holdings": 10,
                        "exchange_breakdown": True
                    },
                    "details": {
                        "balance_by_exchange": True,
                        "asset_allocation": True,
                        "position_summary": True
                    },
                    "charts": {
                        "asset_allocation_chart": True,
                        "performance_chart": True,
                        "exchange_distribution": True
                    }
                },
                styling={
                    "color_scheme": "professional",
                    "font_family": "Arial",
                    "header_color": "#2c3e50",
                    "accent_color": "#3498db",
                    "text_color": "#2c3e50",
                    "background_color": "#ffffff"
                }
            ),
            
            "pnl_analysis_default": ReportTemplate(
                template_id="pnl_analysis_default", 
                name="PnL Analysis (Default)",
                description="Detailed profit and loss analysis with performance metrics",
                report_type="PNL_ANALYSIS",
                sections={
                    "header": {
                        "title": "Profit & Loss Analysis Report",
                        "subtitle": "Trading Performance and Risk Assessment",
                        "include_logo": True,
                        "company_name": "Crypto Trading Terminal"
                    },
                    "summary": {
                        "total_realized_pnl": True,
                        "total_unrealized_pnl": True,
                        "win_rate": True,
                        "total_trades": True
                    },
                    "breakdown": {
                        "pnl_by_exchange": True,
                        "pnl_by_asset": True,
                        "pnl_by_strategy": True,
                        "best_worst_trades": 5
                    },
                    "analytics": {
                        "sharpe_ratio": True,
                        "max_drawdown": True,
                        "volatility": True,
                        "annualized_return": True
                    },
                    "charts": {
                        "pnl_time_series": True,
                        "pnl_distribution": True,
                        "win_rate_chart": True,
                        "drawdown_chart": True
                    }
                },
                styling={
                    "color_scheme": "financial",
                    "font_family": "Arial",
                    "header_color": "#1a472a",
                    "accent_color": "#27ae60",
                    "profit_color": "#27ae60",
                    "loss_color": "#e74c3c",
                    "neutral_color": "#7f8c8d"
                }
            ),
            
            "risk_assessment_default": ReportTemplate(
                template_id="risk_assessment_default",
                name="Risk Assessment (Default)", 
                description="Comprehensive risk analysis and exposure reporting",
                report_type="RISK_ASSESSMENT",
                sections={
                    "header": {
                        "title": "Risk Assessment Report",
                        "subtitle": "Portfolio Risk Analysis and Exposure Assessment",
                        "include_logo": True,
                        "company_name": "Crypto Trading Terminal"
                    },
                    "risk_metrics": {
                        "var_1d": True,
                        "var_7d": True,
                        "max_position_risk": True,
                        "leverage_utilization": True,
                        "overall_risk_score": True
                    },
                    "exposure": {
                        "exposure_by_exchange": True,
                        "exposure_by_asset": True,
                        "concentration_risk": True,
                        "liquidation_risk": True
                    },
                    "stress_testing": {
                        "market_shock_scenarios": True,
                        "correlation_breakdown": True,
                        "tail_risk_analysis": True
                    },
                    "charts": {
                        "risk_heatmap": True,
                        "exposure_pie_charts": True,
                        "var_timeseries": True
                    }
                },
                styling={
                    "color_scheme": "risk",
                    "font_family": "Arial", 
                    "header_color": "#c0392b",
                    "accent_color": "#e74c3c",
                    "low_risk_color": "#27ae60",
                    "medium_risk_color": "#f39c12",
                    "high_risk_color": "#e74c3c"
                }
            ),
            
            "trade_history_default": ReportTemplate(
                template_id="trade_history_default",
                name="Trade History (Default)",
                description="Detailed trade execution history and analysis",
                report_type="TRADE_HISTORY",
                sections={
                    "header": {
                        "title": "Trade History Report",
                        "subtitle": "Complete Trading Activity and Execution Analysis",
                        "include_logo": True,
                        "company_name": "Crypto Trading Terminal"
                    },
                    "summary": {
                        "total_trades": True,
                        "total_volume": True,
                        "total_fees": True,
                        "average_trade_size": True
                    },
                    "trade_details": {
                        "individual_trades": True,
                        "trade_execution_time": True,
                        "slippage_analysis": True,
                        "fee_breakdown": True
                    },
                    "analysis": {
                        "trade_frequency": True,
                        "execution_quality": True,
                        "best_worst_execution": 10
                    },
                    "charts": {
                        "trade_volume_timeline": True,
                        "execution_time_distribution": True,
                        "fee_analysis": True
                    }
                },
                styling={
                    "color_scheme": "trading",
                    "font_family": "Arial",
                    "header_color": "#34495e",
                    "accent_color": "#3498db",
                    "buy_color": "#27ae60",
                    "sell_color": "#e74c3c"
                }
            )
        }
    
    def get_template(self, template_id: str) -> Optional[ReportTemplate]:
        """Get template by ID"""
        return self.templates.get(template_id)
    
    def get_templates_by_type(self, report_type: str) -> Dict[str, ReportTemplate]:
        """Get all templates for a specific report type"""
        return {
            template_id: template 
            for template_id, template in self.templates.items()
            if template.report_type == report_type
        }
    
    def create_custom_template(self, template: ReportTemplate) -> None:
        """Add a custom template"""
        self.templates[template.template_id] = template
    
    def get_available_templates(self) -> Dict[str, ReportTemplate]:
        """Get all available templates"""
        return self.templates.copy()
    
    def validate_template(self, template: ReportTemplate) -> bool:
        """Validate template configuration"""
        required_fields = [
            'template_id', 'name', 'description', 'report_type', 
            'sections', 'styling'
        ]
        
        for field in required_fields:
            if not hasattr(template, field) or not getattr(template, field):
                return False
        
        # Validate sections structure
        if not isinstance(template.sections, dict):
            return False
            
        # Validate styling structure  
        if not isinstance(template.styling, dict):
            return False
        
        return True