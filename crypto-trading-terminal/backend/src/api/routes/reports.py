"""
Report generation API routes
Provides endpoints for PDF/CSV report generation and download
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from enum import Enum
import asyncio
import os
from pathlib import Path

# Import report components
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '../../../backend/src'))

from reports.report_generator import ReportGenerator
from reports.report_types import ReportRequest, ReportType, ExportFormat
from reports.report_templates import ReportTemplateManager


router = APIRouter(prefix="/reports", tags=["reports"])

# Global report generator instance
_report_generator = None
_template_manager = ReportTemplateManager()


def get_report_generator() -> ReportGenerator:
    """Get or create report generator instance"""
    global _report_generator
    if _report_generator is None:
        _report_generator = ReportGenerator()
    return _report_generator


class ReportTypeEnum(str, Enum):
    """Report type enumeration"""
    ACCOUNT_SUMMARY = "account_summary"
    POSITION_DETAIL = "position_detail"
    PNL_ANALYSIS = "pnl_analysis"
    PERFORMANCE_METRICS = "performance_metrics"
    RISK_ASSESSMENT = "risk_assessment"
    TRADE_HISTORY = "trade_history"
    PORTFOLIO_SUMMARY = "portfolio_summary"


class ExportFormatEnum(str, Enum):
    """Export format enumeration"""
    PDF = "pdf"
    CSV = "csv"
    JSON = "json"


class ReportRequestModel(BaseModel):
    """Report generation request model"""
    report_type: ReportTypeEnum = Field(..., description="Type of report to generate")
    export_format: ExportFormatEnum = Field(..., description="Export format")
    start_date: datetime = Field(..., description="Report start date")
    end_date: datetime = Field(..., description="Report end date")
    exchanges: Optional[List[str]] = Field(None, description="Specific exchanges to include")
    assets: Optional[List[str]] = Field(None, description="Specific assets to include")
    include_charts: bool = Field(True, description="Include charts in report")
    template_id: Optional[str] = Field(None, description="Custom template ID")
    custom_parameters: Optional[Dict[str, str]] = Field(None, description="Custom parameters")


class ReportResponseModel(BaseModel):
    """Report generation response model"""
    report_id: str
    file_path: str
    file_size: int
    download_url: str
    expires_at: datetime
    generation_time: float
    format: ExportFormatEnum
    report_type: ReportTypeEnum
    status: str = "completed"


class ReportTemplateModel(BaseModel):
    """Report template model"""
    template_id: str
    name: str
    description: str
    report_type: str
    sections: Dict[str, Any]
    styling: Dict[str, Any]


class ReportListResponse(BaseModel):
    """Report list response model"""
    reports: List[ReportResponseModel]
    total: int


@router.post("/generate", response_model=ReportResponseModel)
async def generate_report(
    request: ReportRequestModel,
    background_tasks: BackgroundTasks,
    report_generator: ReportGenerator = Depends(get_report_generator)
):
    """Generate a new report"""
    try:
        # Convert request model to internal format
        internal_request = ReportRequest(
            report_type=ReportType(request.report_type.value),
            export_format=ExportFormat(request.export_format.value),
            start_date=request.start_date,
            end_date=request.end_date,
            exchanges=request.exchanges,
            assets=request.assets,
            include_charts=request.include_charts,
            template_id=request.template_id,
            custom_parameters=request.custom_parameters
        )
        
        # Validate request
        if internal_request.start_date >= internal_request.end_date:
            raise HTTPException(status_code=400, detail="Start date must be before end date")
        
        if (internal_request.end_date - internal_request.start_date).days > 365:
            raise HTTPException(status_code=400, detail="Report period cannot exceed 1 year")
        
        # Generate report
        response = await report_generator.generate_report(internal_request)
        
        # Clean up old reports in background
        background_tasks.add_task(cleanup_old_reports)
        
        return ReportResponseModel(
            report_id=response.report_id,
            file_path=response.file_path,
            file_size=response.file_size,
            download_url=response.download_url,
            expires_at=response.expires_at,
            generation_time=response.generation_time,
            format=ExportFormatEnum(response.format.value),
            report_type=ReportTypeEnum(response.report_type.value)
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate report: {str(e)}")


@router.get("/download/{report_id}")
async def download_report(
    report_id: str,
    report_generator: ReportGenerator = Depends(get_report_generator)
):
    """Download a generated report"""
    try:
        file_path = Path(report_generator.output_directory) / f"{report_id}.pdf"
        
        # Check if file exists
        if not file_path.exists():
            # Try CSV extension
            file_path = Path(report_generator.output_directory) / f"{report_id}.csv"
            if not file_path.exists():
                raise HTTPException(status_code=404, detail="Report not found")
        
        # Check if file is expired
        file_stat = file_path.stat()
        file_modified = datetime.fromtimestamp(file_stat.st_mtime)
        if datetime.now() - file_modified > timedelta(days=7):
            # Clean up expired file
            file_path.unlink()
            raise HTTPException(status_code=404, detail="Report has expired")
        
        # Determine content type
        if file_path.suffix.lower() == '.pdf':
            media_type = 'application/pdf'
            filename = f"trading_report_{report_id}.pdf"
        elif file_path.suffix.lower() == '.csv':
            media_type = 'text/csv'
            filename = f"trading_report_{report_id}.csv"
        else:
            media_type = 'application/octet-stream'
            filename = f"trading_report_{report_id}"
        
        return FileResponse(
            path=str(file_path),
            media_type=media_type,
            filename=filename
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to download report: {str(e)}")


@router.get("/templates", response_model=List[ReportTemplateModel])
async def get_report_templates():
    """Get available report templates"""
    try:
        templates = _template_manager.get_available_templates()
        
        return [
            ReportTemplateModel(
                template_id=template.template_id,
                name=template.name,
                description=template.description,
                report_type=template.report_type,
                sections=template.sections,
                styling=template.styling
            )
            for template in templates.values()
        ]
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get templates: {str(e)}")


@router.get("/templates/{report_type}", response_model=List[ReportTemplateModel])
async def get_templates_by_type(report_type: ReportTypeEnum):
    """Get templates for a specific report type"""
    try:
        templates = _template_manager.get_templates_by_type(report_type.value.upper())
        
        return [
            ReportTemplateModel(
                template_id=template.template_id,
                name=template.name,
                description=template.description,
                report_type=template.report_type,
                sections=template.sections,
                styling=template.styling
            )
            for template in templates.values()
        ]
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get templates: {str(e)}")


@router.get("/list", response_model=ReportListResponse)
async def list_reports(
    limit: int = 50,
    offset: int = 0,
    report_generator: ReportGenerator = Depends(get_report_generator)
):
    """List generated reports"""
    try:
        reports_dir = Path(report_generator.output_directory)
        
        if not reports_dir.exists():
            return ReportListResponse(reports=[], total=0)
        
        # Get all report files
        report_files = []
        for file_path in reports_dir.iterdir():
            if file_path.is_file() and file_path.suffix in ['.pdf', '.csv']:
                stat = file_path.stat()
                file_modified = datetime.fromtimestamp(stat.st_mtime)
                
                # Skip expired files
                if datetime.now() - file_modified <= timedelta(days=7):
                    report_files.append({
                        'file_path': str(file_path),
                        'file_size': stat.st_size,
                        'modified': file_modified,
                        'report_id': file_path.stem
                    })
        
        # Sort by modification date (newest first)
        report_files.sort(key=lambda x: x['modified'], reverse=True)
        
        # Apply pagination
        paginated_files = report_files[offset:offset + limit]
        
        # Convert to response model
        reports = []
        for file_info in paginated_files:
            try:
                # Determine format and type from file or additional metadata
                format_enum = ExportFormatEnum.CSV if file_info['file_path'].endswith('.csv') else ExportFormatEnum.PDF
                
                # For now, assume account summary type (in real implementation, 
                # this would be stored in metadata)
                report_type = ReportTypeEnum.ACCOUNT_SUMMARY
                
                reports.append(ReportResponseModel(
                    report_id=file_info['report_id'],
                    file_path=file_info['file_path'],
                    file_size=file_info['file_size'],
                    download_url=f"/api/reports/download/{file_info['report_id']}",
                    expires_at=file_info['modified'] + timedelta(days=7),
                    generation_time=0.0,  # Would be stored in metadata
                    format=format_enum,
                    report_type=report_type,
                    status="completed"
                ))
            except Exception:
                # Skip files that can't be processed
                continue
        
        return ReportListResponse(reports=reports, total=len(report_files))
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list reports: {str(e)}")


@router.delete("/delete/{report_id}")
async def delete_report(
    report_id: str,
    report_generator: ReportGenerator = Depends(get_report_generator)
):
    """Delete a generated report"""
    try:
        reports_dir = Path(report_generator.output_directory)
        
        # Find and delete the report file
        deleted = False
        for extension in ['.pdf', '.csv']:
            file_path = reports_dir / f"{report_id}{extension}"
            if file_path.exists():
                file_path.unlink()
                deleted = True
                break
        
        if not deleted:
            raise HTTPException(status_code=404, detail="Report not found")
        
        return {"message": f"Report {report_id} deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete report: {str(e)}")


@router.get("/health")
async def reports_health_check():
    """Health check for reports service"""
    try:
        generator = get_report_generator()
        templates_count = len(_template_manager.get_available_templates())
        
        return {
            "status": "healthy",
            "service": "reports",
            "templates_available": templates_count,
            "output_directory": str(generator.output_directory),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        return {
            "status": "unhealthy",
            "service": "reports",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }


async def cleanup_old_reports():
    """Background task to clean up old report files"""
    try:
        generator = get_report_generator()
        reports_dir = Path(generator.output_directory)
        
        if not reports_dir.exists():
            return
        
        # Remove files older than 7 days
        cutoff_date = datetime.now() - timedelta(days=7)
        
        for file_path in reports_dir.iterdir():
            if file_path.is_file():
                file_modified = datetime.fromtimestamp(file_path.stat().st_mtime)
                if file_modified < cutoff_date:
                    try:
                        file_path.unlink()
                    except Exception:
                        # Continue cleaning even if some files fail
                        continue
        
    except Exception:
        # Silently fail cleanup task
        pass