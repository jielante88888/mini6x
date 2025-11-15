"""
CSV report generator
Creates clean CSV files for data analysis and import into spreadsheet applications
"""

import csv
import asyncio
from datetime import datetime
from decimal import Decimal
from typing import Dict, Any, List
from pathlib import Path


class CSVReportGenerator:
    """Generates CSV reports from trading data"""
    
    async def generate(self, report_data: Dict[str, Any], template, file_path: str):
        """Generate CSV report"""
        try:
            with open(file_path, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile)
                
                # Write header information
                await self._write_report_header(writer, report_data, template)
                
                # Write main content sections
                await self._write_main_content(writer, report_data, template)
                
                # Write summary data
                await self._write_summary(writer, report_data, template)
                
        except Exception as e:
            # Fallback: write basic CSV with error info
            await self._write_fallback_csv(file_path, report_data, str(e))
    
    async def _write_report_header(self, writer, report_data: Dict[str, Any], template):
        """Write report header information"""
        # Report metadata
        writer.writerow(['Report Information'])
        writer.writerow(['Generated', datetime.now().strftime('%Y-%m-%d %H:%M:%S')])
        writer.writerow(['Report Type', template.name])
        writer.writerow(['Template ID', template.template_id])
        
        if 'request' in report_data:
            request = report_data['request']
            writer.writerow(['Start Date', request.start_date.strftime('%Y-%m-%d')])
            writer.writerow(['End Date', request.end_date.strftime('%Y-%m-%d')])
        
        writer.writerow([])  # Empty row for spacing
        
        # Report title
        title = template.sections.get('header', {}).get('title', 'Trading Report')
        writer.writerow([title])
        writer.writerow([])
    
    async def _write_main_content(self, writer, report_data: Dict[str, Any], template):
        """Write main content sections"""
        
        # Account balances section
        if 'accounts' in report_data:
            await self._write_account_section(writer, report_data)
        
        # Positions section
        if 'positions' in report_data:
            await self._write_positions_section(writer, report_data)
        
        # P&L breakdown section
        if 'pnl_by_exchange' in report_data or 'pnl_by_asset' in report_data:
            await self._write_pnl_section(writer, report_data)
        
        # Risk assessment section
        if 'risk_metrics' in report_data:
            await self._write_risk_section(writer, report_data)
        
        # Trade history section
        if 'trade_history' in report_data:
            await self._write_trade_section(writer, report_data)
        
        # Performance metrics section
        if 'period_performance' in report_data:
            await self._write_performance_section(writer, report_data)
    
    async def _write_account_section(self, writer, report_data: Dict[str, Any]):
        """Write account balances section"""
        accounts = report_data['accounts']
        
        writer.writerow(['Account Balances'])
        writer.writerow(['Asset', 'Free Balance', 'Locked Balance', 'Total Balance', 'USD Value', 'Exchange', 'Account Type'])
        
        for account in accounts:
            writer.writerow([
                account.asset,
                str(account.free_balance),
                str(account.locked_balance),
                str(account.total_balance),
                str(account.usd_value) if account.usd_value else '',
                account.exchange,
                account.account_type
            ])
        
        writer.writerow([])  # Empty row for spacing
        
        # Exchange breakdown
        if 'exchange_breakdown' in report_data:
            writer.writerow(['Exchange Breakdown'])
            writer.writerow(['Exchange', 'Total Value (USD)'])
            
            for exchange, value in report_data['exchange_breakdown'].items():
                writer.writerow([exchange, str(value)])
            
            writer.writerow([])
        
        # Asset allocation
        if 'asset_allocation' in report_data:
            writer.writerow(['Asset Allocation'])
            writer.writerow(['Asset', 'Allocation (USD)'])
            
            for asset, value in report_data['asset_allocation'].items():
                writer.writerow([asset, str(value)])
            
            writer.writerow([])
    
    async def _write_positions_section(self, writer, report_data: Dict[str, Any]):
        """Write positions section"""
        positions = report_data['positions']
        
        writer.writerow(['Open Positions'])
        writer.writerow([
            'Symbol', 'Exchange', 'Side', 'Quantity', 'Entry Price', 'Current Price',
            'Current Value', 'Unrealized P&L', 'P&L %', 'Leverage', 'Margin Used', 'Account Type'
        ])
        
        for position in positions:
            current_value = position.current_price * position.quantity
            pnl_percent = (position.unrealized_pnl / (position.entry_price * position.quantity)) * 100 if position.entry_price > 0 else 0
            
            writer.writerow([
                position.symbol,
                position.exchange,
                position.side,
                str(position.quantity),
                str(position.entry_price),
                str(position.current_price),
                str(current_value),
                str(position.unrealized_pnl),
                f"{pnl_percent:.2f}%",
                str(position.leverage) if position.leverage else '',
                str(position.margin_used) if position.margin_used else '',
                position.account_type
            ])
        
        # Position summary
        if 'total_positions' in report_data:
            writer.writerow([])
            writer.writerow(['Position Summary'])
            writer.writerow(['Total Positions', report_data['total_positions']])
            writer.writerow(['Total Margin Used', str(report_data.get('total_margin_used', 0))])
            writer.writerow(['Total Unrealized P&L', str(report_data.get('total_unrealized_pnl', 0))])
            writer.writerow([])
    
    async def _write_pnl_section(self, writer, report_data: Dict[str, Any]):
        """Write P&L section"""
        writer.writerow(['P&L Analysis'])
        
        # P&L summary
        if 'pnl_summary' in report_data:
            pnl = report_data['pnl_summary']
            writer.writerow(['P&L Summary'])
            writer.writerow(['Total Realized P&L', str(pnl.total_realized_pnl)])
            writer.writerow(['Total Unrealized P&L', str(pnl.total_unrealized_pnl)])
            writer.writerow(['Total P&L', str(pnl.total_pnl)])
            writer.writerow(['Daily P&L', str(pnl.daily_pnl)])
            writer.writerow(['Weekly P&L', str(pnl.weekly_pnl)])
            writer.writerow(['Monthly P&L', str(pnl.monthly_pnl)])
            writer.writerow(['Win Rate', f"{pnl.win_rate:.2f}%"])
            writer.writerow(['Total Trades', pnl.total_trades])
            writer.writerow(['Winning Trades', pnl.winning_trades])
            writer.writerow(['Losing Trades', pnl.losing_trades])
            writer.writerow([])
        
        # P&L by exchange
        if 'pnl_by_exchange' in report_data:
            writer.writerow(['P&L by Exchange'])
            writer.writerow(['Exchange', 'P&L'])
            
            for exchange, pnl in report_data['pnl_by_exchange'].items():
                writer.writerow([exchange, str(pnl)])
            
            writer.writerow([])
        
        # P&L by asset
        if 'pnl_by_asset' in report_data:
            writer.writerow(['P&L by Asset'])
            writer.writerow(['Asset', 'P&L'])
            
            for asset, pnl in report_data['pnl_by_asset'].items():
                writer.writerow([asset, str(pnl)])
            
            writer.writerow([])
    
    async def _write_risk_section(self, writer, report_data: Dict[str, Any]):
        """Write risk assessment section"""
        risk_metrics = report_data['risk_metrics']
        
        writer.writerow(['Risk Assessment'])
        writer.writerow(['Risk Metric', 'Value'])
        writer.writerow(['Overall Risk Score', f"{risk_metrics.overall_risk_score:.1f}/10"])
        writer.writerow(['1-Day VaR', str(risk_metrics.value_at_risk_1d)])
        writer.writerow(['7-Day VaR', str(risk_metrics.value_at_risk_7d)])
        writer.writerow(['Max Position Risk', f"{risk_metrics.max_position_risk:.1f}%"])
        writer.writerow(['Leverage Utilization', f"{risk_metrics.leverage_utilization:.1f}%"])
        writer.writerow(['Liquidation Risk', f"{risk_metrics.liquidation_risk:.1f}%"])
        writer.writerow(['Concentration Risk', f"{risk_metrics.concentration_risk:.1f}%"])
        writer.writerow([])
        
        # Risk alerts
        if 'risk_alerts' in report_data:
            writer.writerow(['Risk Alerts'])
            writer.writerow(['Type', 'Message', 'Severity'])
            
            for alert in report_data['risk_alerts']:
                writer.writerow([alert['type'], alert['message'], alert['severity']])
            
            writer.writerow([])
        
        # Recommendations
        if 'recommendations' in report_data:
            writer.writerow(['Recommendations'])
            for i, recommendation in enumerate(report_data['recommendations'], 1):
                writer.writerow([f"Recommendation {i}", recommendation])
            writer.writerow([])
    
    async def _write_trade_section(self, writer, report_data: Dict[str, Any]):
        """Write trade history section"""
        trades = report_data['trade_history']
        
        writer.writerow(['Trade History'])
        writer.writerow([
            'Trade ID', 'Symbol', 'Exchange', 'Side', 'Quantity', 'Price', 
            'Total Value', 'Fee', 'Realized P&L', 'Timestamp'
        ])
        
        for trade in trades:
            total_value = trade.quantity * trade.price
            
            writer.writerow([
                trade.id,
                trade.symbol,
                trade.exchange,
                trade.side,
                str(trade.quantity),
                str(trade.price),
                str(total_value),
                str(trade.fee),
                str(trade.realized_pnl) if trade.realized_pnl else '',
                trade.timestamp.strftime('%Y-%m-%d %H:%M:%S')
            ])
        
        # Trade summary
        if 'total_trades' in report_data:
            writer.writerow([])
            writer.writerow(['Trade Summary'])
            writer.writerow(['Total Trades', report_data['total_trades']])
            writer.writerow(['Total Volume', str(report_data.get('total_volume', 0))])
            writer.writerow(['Total Fees', str(report_data.get('total_fees', 0))])
            writer.writerow([])
    
    async def _write_performance_section(self, writer, report_data: Dict[str, Any]):
        """Write performance metrics section"""
        period_performance = report_data['period_performance']
        
        writer.writerow(['Performance Metrics'])
        writer.writerow(['Period', 'Total Return %', 'Sharpe Ratio', 'Max Drawdown %'])
        
        for period, metrics in period_performance.items():
            writer.writerow([
                period,
                f"{metrics.total_return:.2f}%" if metrics.total_return else '',
                f"{metrics.sharpe_ratio:.2f}" if metrics.sharpe_ratio else '',
                f"{metrics.max_drawdown:.2f}%" if metrics.max_drawdown else ''
            ])
        
        writer.writerow([])
    
    async def _write_summary(self, writer, report_data: Dict[str, Any], template):
        """Write summary section"""
        writer.writerow(['Report Summary'])
        
        # Key metrics summary
        summary_data = []
        
        if 'total_portfolio_value' in report_data:
            summary_data.append(['Total Portfolio Value', f"${report_data['total_portfolio_value']:,.2f}"])
        
        if 'pnl_summary' in report_data:
            pnl = report_data['pnl_summary']
            summary_data.append(['Total P&L', f"${pnl.total_pnl:,.2f}"])
            summary_data.append(['Win Rate', f"{pnl.win_rate:.1f}%"])
        
        if 'risk_metrics' in report_data:
            summary_data.append(['Risk Score', f"{report_data['risk_metrics'].overall_risk_score:.1f}/10"])
        
        if summary_data:
            writer.writerow(['Metric', 'Value'])
            for metric, value in summary_data:
                writer.writerow([metric, value])
            writer.writerow([])
        
        # Footer
        writer.writerow(['Report Footer'])
        writer.writerow(['Generated by', 'Crypto Trading Terminal'])
        writer.writerow(['Generation Time', datetime.now().strftime('%Y-%m-%d %H:%M:%S')])
        writer.writerow(['Template', template.template_id])
    
    async def _write_fallback_csv(self, file_path: str, report_data: Dict[str, Any], error_msg: str):
        """Write fallback CSV with basic information"""
        with open(file_path, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            
            writer.writerow(['Error Report Generated'])
            writer.writerow(['Error Message', error_msg])
            writer.writerow(['Generated', datetime.now().strftime('%Y-%m-%d %H:%M:%S')])
            writer.writerow([])
            
            writer.writerow(['Available Data'])
            for key, value in report_data.items():
                if isinstance(value, (str, int, float, Decimal)):
                    writer.writerow([key, str(value)])
                elif isinstance(value, list):
                    writer.writerow([f"{key} (list)", f"{len(value)} items"])
                elif isinstance(value, dict):
                    writer.writerow([f"{key} (dict)", f"{len(value)} keys"])