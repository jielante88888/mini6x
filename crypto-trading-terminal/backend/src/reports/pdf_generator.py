"""
PDF report generator using reportlab
Creates professional PDF reports with charts and formatting
"""

import asyncio
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, Any, List
from pathlib import Path

try:
    from reportlab.lib.pagesizes import letter, A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.lib import colors
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
    from reportlab.platypus import PageBreak, KeepTogether
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT, TA_JUSTIFY
    from reportlab.pdfgen import canvas
    from reportlab.graphics.shapes import Drawing, Rect, Line
    from reportlab.graphics.charts.piecharts import Pie
    from reportlab.graphics.charts.linecharts import HorizontalLineChart
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False


class PDFReportGenerator:
    """Generates PDF reports with professional formatting"""
    
    def __init__(self):
        if REPORTLAB_AVAILABLE:
            self.page_size = A4
            self.margin = 0.75 * inch
        else:
            self.page_size = None
            self.margin = None
        self.styles = self._create_styles() if REPORTLAB_AVAILABLE else None
    
    async def generate(self, report_data: Dict[str, Any], template, file_path: str):
        """Generate PDF report"""
        if not REPORTLAB_AVAILABLE or not self.styles:
            # Fallback: create a simple text-based PDF
            await self._generate_simple_pdf(report_data, file_path)
            return
        
        try:
            doc = SimpleDocTemplate(
                file_path,
                pagesize=self.page_size,
                rightMargin=self.margin,
                leftMargin=self.margin,
                topMargin=self.margin,
                bottomMargin=self.margin
            )
            
            # Build report content
            story = []
            
            # Add header
            story.extend(await self._add_header(report_data, template))
            
            # Add summary section
            if self._should_include_section(template, "summary"):
                story.extend(await self._add_summary_section(report_data, template))
            
            # Add detailed sections based on report type
            story.extend(await self._add_detailed_sections(report_data, template))
            
            # Add charts if requested
            if report_data.get("request", {}).get("include_charts", True):
                story.extend(await self._add_charts_section(report_data, template))
            
            # Add footer
            story.append(PageBreak())
            story.extend(await self._add_footer(report_data))
            
            # Build PDF
            doc.build(story)
            
        except Exception as e:
            # Fallback to simple PDF if reportlab fails
            await self._generate_simple_pdf(report_data, file_path)
    
    def _create_styles(self):
        """Create custom paragraph styles"""
        if not REPORTLAB_AVAILABLE:
            return None
            
        try:
            styles = getSampleStyleSheet()
            
            # Custom styles
            styles.add(ParagraphStyle(
                name='CustomTitle',
                parent=styles['Title'],
                fontSize=24,
                textColor=colors.HexColor("#2c3e50"),
                alignment=TA_CENTER,
                spaceAfter=30
            ))
            
            styles.add(ParagraphStyle(
                name='CustomHeading1',
                parent=styles['Heading1'],
                fontSize=16,
                textColor=colors.HexColor("#2c3e50"),
                spaceBefore=20,
                spaceAfter=12
            ))
            
            styles.add(ParagraphStyle(
                name='CustomHeading2',
                parent=styles['Heading2'],
                fontSize=14,
                textColor=colors.HexColor("#3498db"),
                spaceBefore=16,
                spaceAfter=10
            ))
            
            styles.add(ParagraphStyle(
                name='CustomBody',
                parent=styles['Normal'],
                fontSize=10,
                textColor=colors.HexColor("#2c3e50"),
                alignment=TA_LEFT,
                spaceAfter=6
            ))
            
            styles.add(ParagraphStyle(
                name='CustomBodyRight',
                parent=styles['Normal'],
                fontSize=10,
                textColor=colors.HexColor("#2c3e50"),
                alignment=TA_RIGHT,
                spaceAfter=6
            ))
            
            return styles
        except Exception:
            return None
    
    async def _add_header(self, report_data: Dict[str, Any], template) -> List:
        """Add report header"""
        story = []
        
        # Company logo and title
        title = template.sections.get("header", {}).get("title", "Trading Report")
        subtitle = template.sections.get("header", {}).get("subtitle", "")
        
        story.append(Paragraph(title, self.styles['CustomTitle']))
        if subtitle:
            story.append(Paragraph(subtitle, self.styles['CustomHeading2']))
        
        story.append(Spacer(1, 0.3 * inch))
        
        # Report metadata
        metadata_data = [
            ['Generated:', datetime.now().strftime("%Y-%m-%d %H:%M:%S")],
            ['Report Period:', f"{report_data['report_period']['start_date'].strftime('%Y-%m-%d')} to {report_data['report_period']['end_date'].strftime('%Y-%m-%d')}"],
            ['Generated by:', 'Crypto Trading Terminal'],
            ['Report ID:', report_data.get('request', {}).get('report_id', 'N/A')]
        ]
        
        metadata_table = Table(metadata_data, colWidths=[1.5*inch, 3*inch])
        metadata_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ]))
        
        story.append(metadata_table)
        story.append(Spacer(1, 0.5 * inch))
        
        return story
    
    async def _add_summary_section(self, report_data: Dict[str, Any], template) -> List:
        """Add summary section"""
        story = []
        
        story.append(Paragraph("Executive Summary", self.styles['CustomHeading1']))
        story.append(Spacer(1, 0.2 * inch))
        
        # Extract summary data based on what's available
        summary_items = []
        
        if "total_portfolio_value" in report_data:
            portfolio_value = report_data["total_portfolio_value"]
            summary_items.append(['Total Portfolio Value', f"${portfolio_value:,.2f}"])
        
        if "pnl_summary" in report_data:
            pnl = report_data["pnl_summary"]
            summary_items.extend([
                ['Total Realized P&L', f"${pnl.total_realized_pnl:,.2f}"],
                ['Total Unrealized P&L', f"${pnl.total_unrealized_pnl:,.2f}"],
                ['Win Rate', f"{pnl.win_rate:.1f}%"],
                ['Total Trades', f"{pnl.total_trades:,}"]
            ])
        
        if "total_trades" in report_data:
            summary_items.append(['Total Trades', f"{report_data['total_trades']:,}"])
        
        if "total_volume" in report_data:
            summary_items.append(['Total Volume', f"${report_data['total_volume']:,.2f}"])
        
        if summary_items:
            summary_table = Table(summary_items, colWidths=[2.5*inch, 1.5*inch])
            summary_table.setStyle(TableStyle([
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
                ('GRID', (0, 0), (-1, -1), 1, colors.lightgrey)
            ]))
            
            story.append(summary_table)
            story.append(Spacer(1, 0.3 * inch))
        
        return story
    
    async def _add_detailed_sections(self, report_data: Dict[str, Any], template) -> List:
        """Add detailed sections based on report data"""
        story = []
        
        # Account breakdown
        if "accounts" in report_data:
            story.extend(await self._add_account_details(report_data))
        
        # Position details
        if "positions" in report_data:
            story.extend(await self._add_position_details(report_data))
        
        # P&L breakdown
        if "pnl_by_exchange" in report_data or "pnl_by_asset" in report_data:
            story.extend(await self._add_pnl_breakdown(report_data))
        
        # Risk assessment
        if "risk_metrics" in report_data:
            story.extend(await self._add_risk_details(report_data))
        
        # Trade history
        if "trade_history" in report_data:
            story.extend(await self._add_trade_history(report_data))
        
        return story
    
    async def _add_account_details(self, report_data: Dict[str, Any]) -> List:
        """Add account balance details"""
        story = []
        
        story.append(Paragraph("Account Balances", self.styles['CustomHeading1']))
        story.append(Spacer(1, 0.1 * inch))
        
        accounts = report_data["accounts"]
        
        # Account table data
        account_data = [['Asset', 'Free', 'Locked', 'Total', 'USD Value', 'Exchange']]
        
        for account in accounts:
            account_data.append([
                account.asset,
                f"{account.free_balance:.4f}",
                f"{account.locked_balance:.4f}",
                f"{account.total_balance:.4f}",
                f"${account.usd_value:,.2f}" if account.usd_value else "N/A",
                account.exchange
            ])
        
        account_table = Table(account_data, colWidths=[0.8*inch, 1*inch, 1*inch, 1*inch, 1*inch, 1*inch])
        account_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('ALIGN', (1, 1), (-1, -1), 'RIGHT')
        ]))
        
        story.append(account_table)
        story.append(Spacer(1, 0.3 * inch))
        
        return story
    
    async def _add_position_details(self, report_data: Dict[str, Any]) -> List:
        """Add position details"""
        story = []
        
        story.append(Paragraph("Open Positions", self.styles['CustomHeading1']))
        story.append(Spacer(1, 0.1 * inch))
        
        positions = report_data["positions"]
        
        # Position table data
        position_data = [['Symbol', 'Side', 'Quantity', 'Entry Price', 'Current Price', 'P&L', 'Exchange']]
        
        for position in positions:
            pnl_color = "green" if position.unrealized_pnl >= 0 else "red"
            pnl_str = f"${position.unrealized_pnl:,.2f}"
            
            position_data.append([
                position.symbol,
                position.side.upper(),
                f"{position.quantity:.4f}",
                f"${position.entry_price:,.2f}",
                f"${position.current_price:,.2f}",
                pnl_str,
                position.exchange
            ])
        
        position_table = Table(position_data, colWidths=[1.2*inch, 0.8*inch, 1*inch, 1*inch, 1*inch, 1*inch, 1*inch])
        position_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('ALIGN', (2, 1), (-1, -1), 'RIGHT')
        ]))
        
        story.append(position_table)
        story.append(Spacer(1, 0.3 * inch))
        
        return story
    
    async def _add_pnl_breakdown(self, report_data: Dict[str, Any]) -> List:
        """Add P&L breakdown details"""
        story = []
        
        story.append(Paragraph("P&L Breakdown", self.styles['CustomHeading1']))
        story.append(Spacer(1, 0.1 * inch))
        
        pnl_data = []
        
        if "pnl_by_exchange" in report_data:
            for exchange, pnl in report_data["pnl_by_exchange"].items():
                pnl_data.append(['Exchange', exchange, f"${pnl:,.2f}"])
        
        if "pnl_by_asset" in report_data:
            for asset, pnl in report_data["pnl_by_asset"].items():
                pnl_data.append(['Asset', asset, f"${pnl:,.2f}"])
        
        if pnl_data:
            pnl_table = Table(pnl_data, colWidths=[1*inch, 2*inch, 1.5*inch])
            pnl_table.setStyle(TableStyle([
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                ('FONTNAME', (1, 0), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
                ('GRID', (0, 0), (-1, -1), 1, colors.lightgrey),
                ('ALIGN', (2, 0), (2, -1), 'RIGHT')
            ]))
            
            story.append(pnl_table)
            story.append(Spacer(1, 0.3 * inch))
        
        return story
    
    async def _add_risk_details(self, report_data: Dict[str, Any]) -> List:
        """Add risk assessment details"""
        story = []
        
        story.append(Paragraph("Risk Assessment", self.styles['CustomHeading1']))
        story.append(Spacer(1, 0.1 * inch))
        
        risk_metrics = report_data["risk_metrics"]
        
        risk_data = [
            ['Risk Metric', 'Value'],
            ['Overall Risk Score', f"{risk_metrics.overall_risk_score:.1f}/10"],
            ['1-Day VaR', f"${risk_metrics.value_at_risk_1d:,.2f}"],
            ['7-Day VaR', f"${risk_metrics.value_at_risk_7d:,.2f}"],
            ['Max Position Risk', f"{risk_metrics.max_position_risk:.1f}%"],
            ['Leverage Utilization', f"{risk_metrics.leverage_utilization:.1f}%"],
            ['Liquidation Risk', f"{risk_metrics.liquidation_risk:.1f}%"]
        ]
        
        risk_table = Table(risk_data, colWidths=[2.5*inch, 1.5*inch])
        risk_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('FONTSIZE', (0, 1), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 1, colors.lightgrey)
        ]))
        
        story.append(risk_table)
        
        # Add risk alerts if available
        if "risk_alerts" in report_data and report_data["risk_alerts"]:
            story.append(Spacer(1, 0.2 * inch))
            story.append(Paragraph("Risk Alerts", self.styles['CustomHeading2']))
            
            for alert in report_data["risk_alerts"]:
                severity_color = {
                    "HIGH": colors.red,
                    "MEDIUM": colors.orange,
                    "LOW": colors.yellow
                }.get(alert["severity"], colors.grey)
                
                alert_text = f"• [{alert['severity']}] {alert['message']}"
                alert_para = Paragraph(alert_text, self.styles['CustomBody'])
                story.append(alert_para)
        
        story.append(Spacer(1, 0.3 * inch))
        
        return story
    
    async def _add_trade_history(self, report_data: Dict[str, Any]) -> List:
        """Add trade history details"""
        story = []
        
        story.append(Paragraph("Recent Trade History", self.styles['CustomHeading1']))
        story.append(Spacer(1, 0.1 * inch))
        
        trades = report_data["trade_history"][:20]  # Show last 20 trades
        
        trade_data = [['Time', 'Symbol', 'Side', 'Quantity', 'Price', 'P&L', 'Fee']]
        
        for trade in trades:
            pnl_str = f"${trade.realized_pnl:,.2f}" if trade.realized_pnl else "N/A"
            trade_data.append([
                trade.timestamp.strftime("%m-%d %H:%M"),
                trade.symbol,
                trade.side.upper(),
                f"{trade.quantity:.4f}",
                f"${trade.price:,.2f}",
                pnl_str,
                f"${trade.fee:.2f}"
            ])
        
        trade_table = Table(trade_data, colWidths=[1*inch, 1*inch, 0.7*inch, 1*inch, 1*inch, 1*inch, 0.7*inch])
        trade_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 8),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 7),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        story.append(trade_table)
        story.append(Spacer(1, 0.3 * inch))
        
        return story
    
    async def _add_charts_section(self, report_data: Dict[str, Any], template) -> List:
        """Add charts and visualizations"""
        story = []
        
        story.append(Paragraph("Visual Analysis", self.styles['CustomHeading1']))
        story.append(Spacer(1, 0.2 * inch))
        
        # For now, add placeholder for charts
        # In a full implementation, this would generate actual charts
        
        chart_placeholder = """
        <para>
        <font color="grey" size="10">
        [Charts would be displayed here in a full implementation]<br/>
        • Portfolio Allocation Pie Chart<br/>
        • P&L Time Series Line Chart<br/>
        • Risk Heatmap<br/>
        • Performance Comparison Bar Chart
        </font>
        </para>
        """
        
        story.append(Paragraph(chart_placeholder, self.styles['CustomBody']))
        story.append(Spacer(1, 0.3 * inch))
        
        return story
    
    async def _add_footer(self, report_data: Dict[str, Any]) -> List:
        """Add report footer"""
        story = []
        
        footer_text = """
        <para align="center">
        <font color="grey" size="8">
        This report was generated by Crypto Trading Terminal<br/>
        For questions or support, please contact your system administrator<br/>
        Report generated on %s
        </font>
        </para>
        """ % datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        story.append(Paragraph(footer_text, self.styles['CustomBody']))
        
        return story
    
    def _should_include_section(self, template, section_name: str) -> bool:
        """Check if section should be included based on template"""
        return template.sections.get(section_name, {})
    
    async def _generate_simple_pdf(self, report_data: Dict[str, Any], file_path: str):
        """Generate simple text-based PDF as fallback"""
        if not REPORTLAB_AVAILABLE:
            # If reportlab is not available, create a simple text file instead
            await self._generate_simple_text_file(report_data, file_path.replace('.pdf', '.txt'))
            return
        
        from reportlab.pdfgen import canvas
        
        try:
            c = canvas.Canvas(file_path, pagesize=A4)
            width, height = A4
        except Exception:
            # If A4 is not available, fall back to text file
            await self._generate_simple_text_file(report_data, file_path.replace('.pdf', '.txt'))
            return
        
        # Title
        c.setFont("Helvetica-Bold", 16)
        c.drawString(100, height - 100, "Trading Report")
        
        # Basic info
        c.setFont("Helvetica", 10)
        y_position = height - 150
        
        c.drawString(100, y_position, f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        y_position -= 20
        
        if "total_portfolio_value" in report_data:
            c.drawString(100, y_position, f"Portfolio Value: ${report_data['total_portfolio_value']:,.2f}")
            y_position -= 20
        
        if "pnl_summary" in report_data:
            pnl = report_data["pnl_summary"]
            c.drawString(100, y_position, f"Total P&L: ${pnl.total_pnl:,.2f}")
            y_position -= 20
            c.drawString(100, y_position, f"Win Rate: {pnl.win_rate:.1f}%")
            y_position -= 20
        
        c.save()
    
    async def _generate_simple_text_file(self, report_data: Dict[str, Any], file_path: str):
        """Generate simple text file as fallback when PDF libraries are not available"""
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write("CRYPTO TRADING TERMINAL - TRADING REPORT\n")
            f.write("=" * 50 + "\n\n")
            f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            # Basic report content
            if "total_portfolio_value" in report_data:
                f.write(f"Portfolio Value: ${report_data['total_portfolio_value']:,.2f}\n")
            
            if "pnl_summary" in report_data:
                pnl = report_data["pnl_summary"]
                f.write(f"Total P&L: ${pnl.total_pnl:,.2f}\n")
                f.write(f"Win Rate: {pnl.win_rate:.1f}%\n")
                f.write(f"Total Trades: {pnl.total_trades}\n")
            
            # Account balances
            if "accounts" in report_data:
                f.write("\nAccount Balances:\n")
                for account in report_data["accounts"]:
                    f.write(f"{account.asset}: {account.total_balance} (${account.usd_value})\n")
            
            f.write(f"\nReport generated by Crypto Trading Terminal\n")
            f.write(f"File format: Text (PDF generation not available)\n")