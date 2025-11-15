"""
Main report generation coordinator
Manages the overall report generation process
"""

import asyncio
import uuid
import os
from datetime import datetime, timedelta
from decimal import Decimal
from typing import List, Dict, Optional, Any, Union
from pathlib import Path

from .report_types import (
    ReportRequest, ReportResponse, ReportType, ExportFormat,
    AccountReport, PositionReport, PnLReport, PerformanceReport, RiskReport,
    AccountBalance, Position, TradeRecord, PnLSummary, PerformanceMetrics, RiskMetrics
)
from .pdf_generator import PDFReportGenerator
from .csv_generator import CSVReportGenerator
from .report_templates import ReportTemplateManager


class ReportGenerator:
    """Main report generation coordinator"""
    
    def __init__(self, output_directory: str = "reports"):
        self.output_directory = Path(output_directory)
        self.output_directory.mkdir(exist_ok=True)
        
        self.pdf_generator = PDFReportGenerator()
        self.csv_generator = CSVReportGenerator()
        self.template_manager = ReportTemplateManager()
        
        # Mock data services (replace with actual services)
        self.account_service = None
        self.position_service = None
        self.trade_service = None
        self.pnl_service = None
        self.risk_service = None
    
    def set_data_services(self, account_service, position_service, 
                         trade_service, pnl_service, risk_service):
        """Set data services for report generation"""
        self.account_service = account_service
        self.position_service = position_service
        self.trade_service = trade_service
        self.pnl_service = pnl_service
        self.risk_service = risk_service
    
    async def generate_report(self, request: ReportRequest) -> ReportResponse:
        """Generate report based on request"""
        start_time = datetime.now()
        report_id = str(uuid.uuid4())
        
        try:
            # Collect data based on report type
            report_data = await self._collect_report_data(request)
            
            # Select template
            template = self.template_manager.get_template(
                request.template_id or self._get_default_template_id(request.report_type)
            )
            
            # Generate report file
            if request.export_format == ExportFormat.PDF:
                file_path = await self._generate_pdf_report(
                    report_data, template, report_id, request
                )
            elif request.export_format == ExportFormat.CSV:
                file_path = await self._generate_csv_report(
                    report_data, template, report_id, request
                )
            else:
                raise ValueError(f"Unsupported export format: {request.export_format}")
            
            # Get file info
            file_size = os.path.getsize(file_path)
            
            # Calculate generation time
            generation_time = (datetime.now() - start_time).total_seconds()
            
            # Set expiration (7 days from now)
            expires_at = datetime.now() + timedelta(days=7)
            
            # Generate download URL (in real implementation, this would be a proper URL)
            download_url = f"/api/reports/download/{report_id}"
            
            return ReportResponse(
                report_id=report_id,
                file_path=str(file_path),
                file_size=file_size,
                download_url=download_url,
                expires_at=expires_at,
                generation_time=generation_time,
                format=request.export_format,
                report_type=request.report_type
            )
            
        except Exception as e:
            raise Exception(f"Failed to generate report: {str(e)}")
    
    async def _collect_report_data(self, request: ReportRequest) -> Dict[str, Any]:
        """Collect all data needed for the report"""
        report_data = {
            "request": request,
            "generated_at": datetime.now(),
            "report_period": {
                "start_date": request.start_date,
                "end_date": request.end_date
            }
        }
        
        # Collect data based on report type
        if request.report_type in [ReportType.ACCOUNT_SUMMARY, ReportType.PORTFOLIO_SUMMARY]:
            report_data.update(await self._collect_account_data(request))
        
        if request.report_type in [ReportType.POSITION_DETAIL]:
            report_data.update(await self._collect_position_data(request))
        
        if request.report_type in [ReportType.PNL_ANALYSIS]:
            report_data.update(await self._collect_pnl_data(request))
        
        if request.report_type in [ReportType.PERFORMANCE_METRICS]:
            report_data.update(await self._collect_performance_data(request))
        
        if request.report_type in [ReportType.RISK_ASSESSMENT]:
            report_data.update(await self._collect_risk_data(request))
        
        if request.report_type == ReportType.TRADE_HISTORY:
            report_data.update(await self._collect_trade_data(request))
        
        return report_data
    
    async def _collect_account_data(self, request: ReportRequest) -> Dict[str, Any]:
        """Collect account and balance data"""
        # Mock data - replace with actual service calls
        accounts = [
            AccountBalance(
                asset="BTC",
                free_balance=Decimal("1.5"),
                locked_balance=Decimal("0.2"),
                total_balance=Decimal("1.7"),
                usd_value=Decimal("85000"),
                exchange="binance",
                account_type="spot"
            ),
            AccountBalance(
                asset="ETH",
                free_balance=Decimal("15.0"),
                locked_balance=Decimal("0.0"),
                total_balance=Decimal("15.0"),
                usd_value=Decimal("46500"),
                exchange="okx",
                account_type="spot"
            ),
            AccountBalance(
                asset="USDT",
                free_balance=Decimal("25000"),
                locked_balance=Decimal("5000"),
                total_balance=Decimal("30000"),
                usd_value=Decimal("30000"),
                exchange="binance",
                account_type="spot"
            )
        ]
        
        total_value = sum(acc.usd_value for acc in accounts if acc.usd_value)
        
        return {
            "accounts": accounts,
            "total_portfolio_value": total_value,
            "exchange_breakdown": {
                "binance": Decimal("115000"),
                "okx": Decimal("46500")
            },
            "asset_allocation": {
                "BTC": Decimal("85000"),
                "ETH": Decimal("46500"),
                "USDT": Decimal("30000")
            }
        }
    
    async def _collect_position_data(self, request: ReportRequest) -> Dict[str, Any]:
        """Collect position data"""
        positions = [
            Position(
                symbol="BTCUSDT",
                exchange="binance",
                side="long",
                quantity=Decimal("1.0"),
                entry_price=Decimal("50000"),
                current_price=Decimal("51000"),
                leverage=None,
                margin_used=Decimal("50000"),
                unrealized_pnl=Decimal("1000"),
                account_type="spot"
            ),
            Position(
                symbol="ETHUSDT",
                exchange="okx",
                side="long",
                quantity=Decimal("10.0"),
                entry_price=Decimal("3000"),
                current_price=Decimal("3100"),
                leverage=Decimal("2"),
                margin_used=Decimal("15000"),
                unrealized_pnl=Decimal("1000"),
                liquidation_price=Decimal("2700"),
                account_type="futures"
            )
        ]
        
        return {
            "positions": positions,
            "total_positions": len(positions),
            "total_margin_used": sum(p.margin_used or Decimal("0") for p in positions),
            "total_unrealized_pnl": sum(p.unrealized_pnl for p in positions)
        }
    
    async def _collect_pnl_data(self, request: ReportRequest) -> Dict[str, Any]:
        """Collect PnL data"""
        pnl_summary = PnLSummary(
            total_realized_pnl=Decimal("15000"),
            total_unrealized_pnl=Decimal("2000"),
            total_pnl=Decimal("17000"),
            daily_pnl=Decimal("500"),
            weekly_pnl=Decimal("3000"),
            monthly_pnl=Decimal("12000"),
            win_rate=Decimal("65.5"),
            total_trades=200,
            winning_trades=131,
            losing_trades=69
        )
        
        return {
            "pnl_summary": pnl_summary,
            "pnl_by_exchange": {
                "binance": Decimal("12000"),
                "okx": Decimal("5000")
            },
            "pnl_by_asset": {
                "BTC": Decimal("8000"),
                "ETH": Decimal("6000"),
                "SOL": Decimal("2000")
            }
        }
    
    async def _collect_performance_data(self, request: ReportRequest) -> Dict[str, Any]:
        """Collect performance metrics data"""
        performance_metrics = PerformanceMetrics(
            sharpe_ratio=Decimal("1.45"),
            max_drawdown=Decimal("12.5"),
            volatility=Decimal("18.2"),
            total_return=Decimal("25.8"),
            annualized_return=Decimal("28.5"),
            sortino_ratio=Decimal("1.89"),
            calmar_ratio=Decimal("2.28")
        )
        
        return {
            "period_performance": {
                "1m": PerformanceMetrics(
                    total_return=Decimal("5.2"),
                    sharpe_ratio=Decimal("1.2"),
                    max_drawdown=Decimal("8.5")
                ),
                "3m": PerformanceMetrics(
                    total_return=Decimal("15.8"),
                    sharpe_ratio=Decimal("1.35"),
                    max_drawdown=Decimal("10.2")
                ),
                "6m": PerformanceMetrics(
                    total_return=Decimal("22.1"),
                    sharpe_ratio=Decimal("1.42"),
                    max_drawdown=Decimal("11.8")
                ),
                "1y": performance_metrics
            }
        }
    
    async def _collect_risk_data(self, request: ReportRequest) -> Dict[str, Any]:
        """Collect risk assessment data"""
        risk_metrics = RiskMetrics(
            value_at_risk_1d=Decimal("8500"),
            value_at_risk_7d=Decimal("25000"),
            max_position_risk=Decimal("15.2"),
            leverage_utilization=Decimal("45.8"),
            liquidation_risk=Decimal("2.1"),
            concentration_risk=Decimal("35.6"),
            overall_risk_score=Decimal("6.2")
        )
        
        return {
            "risk_metrics": risk_metrics,
            "risk_by_exchange": {
                "binance": RiskMetrics(
                    overall_risk_score=Decimal("5.8"),
                    value_at_risk_1d=Decimal("5000")
                ),
                "okx": RiskMetrics(
                    overall_risk_score=Decimal("6.8"),
                    value_at_risk_1d=Decimal("3500")
                )
            },
            "risk_alerts": [
                {
                    "type": "CONCENTRATION",
                    "message": "High concentration in BTC positions",
                    "severity": "MEDIUM"
                },
                {
                    "type": "LEVERAGE",
                    "message": "Leverage utilization above 40%",
                    "severity": "LOW"
                }
            ],
            "recommendations": [
                "Consider diversifying position concentration",
                "Monitor leverage utilization closely",
                "Review risk management parameters"
            ]
        }
    
    async def _collect_trade_data(self, request: ReportRequest) -> Dict[str, Any]:
        """Collect trade history data"""
        trades = [
            TradeRecord(
                id="trade_001",
                symbol="BTCUSDT",
                exchange="binance",
                side="buy",
                quantity=Decimal("0.5"),
                price=Decimal("50000"),
                fee=Decimal("25"),
                timestamp=datetime.now() - timedelta(hours=2),
                realized_pnl=Decimal("500")
            ),
            TradeRecord(
                id="trade_002",
                symbol="ETHUSDT",
                exchange="okx",
                side="sell",
                quantity=Decimal("2.0"),
                price=Decimal("3100"),
                fee=Decimal("6.2"),
                timestamp=datetime.now() - timedelta(hours=1),
                realized_pnl=Decimal("200")
            )
        ]
        
        return {
            "trade_history": trades,
            "total_trades": len(trades),
            "total_volume": sum(t.quantity * t.price for t in trades),
            "total_fees": sum(t.fee for t in trades)
        }
    
    def _get_default_template_id(self, report_type: ReportType) -> str:
        """Get default template ID for report type"""
        template_mapping = {
            ReportType.ACCOUNT_SUMMARY: "account_summary_default",
            ReportType.POSITION_DETAIL: "account_summary_default",  # Use same template for now
            ReportType.PNL_ANALYSIS: "pnl_analysis_default",
            ReportType.PERFORMANCE_METRICS: "pnl_analysis_default",
            ReportType.RISK_ASSESSMENT: "risk_assessment_default",
            ReportType.TRADE_HISTORY: "trade_history_default",
            ReportType.PORTFOLIO_SUMMARY: "account_summary_default"
        }
        return template_mapping.get(report_type, "account_summary_default")
    
    async def _generate_pdf_report(self, report_data: Dict[str, Any], 
                                 template, report_id: str, request: ReportRequest) -> str:
        """Generate PDF report"""
        file_path = self.output_directory / f"{report_id}.pdf"
        await self.pdf_generator.generate(report_data, template, str(file_path))
        
        # Check if the actual file was created (it might be a .txt file if reportlab is not available)
        actual_file_path = file_path
        if not file_path.exists():
            # Try text file fallback
            text_file_path = self.output_directory / f"{report_id}.txt"
            if text_file_path.exists():
                actual_file_path = text_file_path
        
        return str(actual_file_path)
    
    async def _generate_csv_report(self, report_data: Dict[str, Any],
                                 template, report_id: str, request: ReportRequest) -> str:
        """Generate CSV report"""
        file_path = self.output_directory / f"{report_id}.csv"
        await self.csv_generator.generate(report_data, template, str(file_path))
        return str(file_path)