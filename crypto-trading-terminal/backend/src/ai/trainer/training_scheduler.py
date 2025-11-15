"""
Training Scheduler
Manages automated training schedules, model retraining, and training job coordination
"""

import asyncio
import schedule
import time
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass
from enum import Enum
import structlog
import json
from pathlib import Path

from ..models.base_model import BaseAIModel
from .model_trainer import ModelTrainer

logger = structlog.get_logger()


class ScheduleFrequency(Enum):
    """Training schedule frequency"""
    HOURLY = "hourly"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    ON_DEMAND = "on_demand"


class TrainingStatus(Enum):
    """Training job status"""
    SCHEDULED = "scheduled"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class TrainingSchedule:
    """Training schedule configuration"""
    schedule_id: str
    model_id: str
    model_type: str
    frequency: ScheduleFrequency
    enabled: bool
    next_run: datetime
    last_run: Optional[datetime]
    parameters: Dict[str, Any]
    created_at: datetime
    updated_at: datetime


@dataclass
class TrainingJob:
    """Training job information"""
    job_id: str
    schedule_id: str
    model_id: str
    status: TrainingStatus
    started_at: datetime
    completed_at: Optional[datetime]
    progress: Decimal
    result: Optional[Dict[str, Any]]
    error: Optional[str]
    metadata: Dict[str, Any]


class TrainingScheduler:
    """Automated training scheduler for AI models"""
    
    def __init__(self, model_trainer: ModelTrainer, config: Optional[Dict[str, Any]] = None):
        self.model_trainer = model_trainer
        self.config = config or {
            "default_retrain_interval_hours": 24,
            "max_concurrent_jobs": 3,
            "job_timeout_hours": 6,
            "schedule_check_interval_minutes": 5,
            "cleanup_completed_jobs_after_days": 7
        }
        
        # Training schedules storage
        self.schedules: Dict[str, TrainingSchedule] = {}
        self.jobs: Dict[str, TrainingJob] = {}
        
        # Active training jobs
        self.active_jobs: Dict[str, TrainingJob] = {}
        
        # Scheduler control
        self.is_running = False
        self.scheduler_task: Optional[asyncio.Task] = None
        
        # Callbacks
        self.job_start_callbacks: List[Callable] = []
        self.job_complete_callbacks: List[Callable] = []
        self.job_error_callbacks: List[Callable] = []
        
        logger.info("训练调度器初始化完成", config=self.config)
    
    async def start_scheduler(self):
        """Start the training scheduler"""
        if self.is_running:
            logger.warning("训练调度器已在运行中")
            return
        
        self.is_running = True
        self.scheduler_task = asyncio.create_task(self._scheduler_loop())
        logger.info("训练调度器已启动")
    
    async def stop_scheduler(self):
        """Stop the training scheduler"""
        if not self.is_running:
            return
        
        self.is_running = False
        
        if self.scheduler_task:
            self.scheduler_task.cancel()
            try:
                await self.scheduler_task
            except asyncio.CancelledError:
                pass
        
        # Cancel active jobs
        for job in list(self.active_jobs.values()):
            await self._cancel_job(job.job_id)
        
        logger.info("训练调度器已停止")
    
    async def _scheduler_loop(self):
        """Main scheduler loop"""
        while self.is_running:
            try:
                # Check for scheduled jobs
                await self._check_scheduled_jobs()
                
                # Clean up old jobs
                await self._cleanup_old_jobs()
                
                # Update schedule next run times
                await self._update_schedule_times()
                
                # Wait before next check
                await asyncio.sleep(self.config["schedule_check_interval_minutes"] * 60)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("调度器循环错误", error=str(e))
                await asyncio.sleep(60)  # Wait 1 minute before retry
    
    async def _check_scheduled_jobs(self):
        """Check for jobs that need to be executed"""
        current_time = datetime.now(timezone.utc)
        
        for schedule in self.schedules.values():
            if not schedule.enabled:
                continue
            
            if current_time >= schedule.next_run:
                if len(self.active_jobs) < self.config["max_concurrent_jobs"]:
                    await self._execute_scheduled_job(schedule)
                else:
                    logger.info("达到最大并发作业数，跳过调度", 
                               schedule_id=schedule.schedule_id,
                               active_jobs=len(self.active_jobs))
    
    async def _execute_scheduled_job(self, schedule: TrainingSchedule):
        """Execute a scheduled training job"""
        job_id = f"job_{schedule.schedule_id}_{int(datetime.now().timestamp())}"
        
        # Create job
        job = TrainingJob(
            job_id=job_id,
            schedule_id=schedule.schedule_id,
            model_id=schedule.model_id,
            status=TrainingStatus.SCHEDULED,
            started_at=datetime.now(timezone.utc),
            completed_at=None,
            progress=Decimal("0.0"),
            result=None,
            error=None,
            metadata={"schedule": schedule.parameters}
        )
        
        self.jobs[job_id] = job
        self.active_jobs[job_id] = job
        
        # Update schedule last run time
        schedule.last_run = datetime.now(timezone.utc)
        
        # Execute job
        asyncio.create_task(self._run_training_job(job))
        
        logger.info("开始执行训练作业", 
                   job_id=job_id,
                   schedule_id=schedule.schedule_id)
    
    async def _run_training_job(self, job: TrainingJob):
        """Run a training job"""
        try:
            # Update job status
            job.status = TrainingStatus.RUNNING
            await self._notify_job_start(job)
            
            # Get schedule details
            schedule = self.schedules[job.schedule_id]
            
            # Update progress
            job.progress = Decimal("0.1")
            
            # Prepare training data (placeholder - would fetch from data pipeline)
            training_data = await self._prepare_training_data(schedule.model_type)
            
            job.progress = Decimal("0.3")
            
            # Start training
            training_result = await self.model_trainer.train_model(
                model_id=schedule.model_id,
                training_data=training_data,
                training_config=schedule.parameters
            )
            
            job.progress = Decimal("0.9")
            
            # Complete job
            job.status = TrainingStatus.COMPLETED
            job.completed_at = datetime.now(timezone.utc)
            job.progress = Decimal("1.0")
            job.result = training_result
            
            logger.info("训练作业完成", 
                       job_id=job.job_id,
                       schedule_id=job.schedule_id)
            
            await self._notify_job_complete(job)
            
        except Exception as e:
            logger.error("训练作业失败", 
                        job_id=job.job_id,
                        error=str(e))
            
            job.status = TrainingStatus.FAILED
            job.completed_at = datetime.now(timezone.utc)
            job.error = str(e)
            
            await self._notify_job_error(job, e)
        
        finally:
            # Remove from active jobs
            if job.job_id in self.active_jobs:
                del self.active_jobs[job.job_id]
    
    async def _prepare_training_data(self, model_type: str) -> List[Dict[str, Any]]:
        """Prepare training data (placeholder implementation)"""
        # In a real implementation, this would fetch data from a data pipeline
        # For now, generate mock training data
        import random
        
        mock_data = []
        for i in range(100):
            sample = {
                "timestamp": datetime.now(timezone.utc) - timedelta(days=i),
                "price": random.uniform(40000, 60000),
                "volume": random.uniform(1000, 5000),
                "rsi": random.uniform(20, 80),
                "macd": random.uniform(-100, 100),
                "symbol": "BTCUSDT"
            }
            mock_data.append(sample)
        
        logger.info("生成模拟训练数据", model_type=model_type, samples=len(mock_data))
        return mock_data
    
    async def _cleanup_old_jobs(self):
        """Clean up old completed jobs"""
        cutoff_time = datetime.now(timezone.utc) - timedelta(
            days=self.config["cleanup_completed_jobs_after_days"]
        )
        
        jobs_to_remove = []
        for job_id, job in self.jobs.items():
            if (job.completed_at and job.completed_at < cutoff_time and
                job.status in [TrainingStatus.COMPLETED, TrainingStatus.FAILED, TrainingStatus.CANCELLED]):
                jobs_to_remove.append(job_id)
        
        for job_id in jobs_to_remove:
            del self.jobs[job_id]
        
        if jobs_to_remove:
            logger.info("清理旧训练作业", count=len(jobs_to_remove))
    
    async def _update_schedule_times(self):
        """Update schedule next run times"""
        current_time = datetime.now(timezone.utc)
        
        for schedule in self.schedules.values():
            if not schedule.enabled:
                continue
            
            if schedule.last_run and current_time >= schedule.next_run:
                # Calculate next run time based on frequency
                if schedule.frequency == ScheduleFrequency.HOURLY:
                    schedule.next_run = schedule.last_run + timedelta(hours=1)
                elif schedule.frequency == ScheduleFrequency.DAILY:
                    schedule.next_run = schedule.last_run + timedelta(days=1)
                elif schedule.frequency == ScheduleFrequency.WEEKLY:
                    schedule.next_run = schedule.last_run + timedelta(weeks=1)
                elif schedule.frequency == ScheduleFrequency.MONTHLY:
                    schedule.next_run = schedule.last_run + timedelta(days=30)
                
                schedule.updated_at = datetime.now(timezone.utc)
    
    async def _cancel_job(self, job_id: str):
        """Cancel a running job"""
        if job_id in self.active_jobs:
            job = self.active_jobs[job_id]
            job.status = TrainingStatus.CANCELLED
            job.completed_at = datetime.now(timezone.utc)
            del self.active_jobs[job_id]
            
            logger.info("已取消训练作业", job_id=job_id)
    
    async def _notify_job_start(self, job: TrainingJob):
        """Notify job start callbacks"""
        for callback in self.job_start_callbacks:
            try:
                await callback(job)
            except Exception as e:
                logger.warning("作业开始回调失败", error=str(e))
    
    async def _notify_job_complete(self, job: TrainingJob):
        """Notify job complete callbacks"""
        for callback in self.job_complete_callbacks:
            try:
                await callback(job)
            except Exception as e:
                logger.warning("作业完成回调失败", error=str(e))
    
    async def _notify_job_error(self, job: TrainingJob, error: Exception):
        """Notify job error callbacks"""
        for callback in self.job_error_callbacks:
            try:
                await callback(job, error)
            except Exception as e:
                logger.warning("作业错误回调失败", error=str(e))
    
    def create_schedule(self, model_id: str, model_type: str, 
                       frequency: ScheduleFrequency, 
                       parameters: Dict[str, Any] = None) -> str:
        """Create a new training schedule"""
        schedule_id = f"sched_{model_id}_{int(datetime.now().timestamp())}"
        
        # Calculate initial next run time
        current_time = datetime.now(timezone.utc)
        if frequency == ScheduleFrequency.HOURLY:
            next_run = current_time + timedelta(hours=1)
        elif frequency == ScheduleFrequency.DAILY:
            next_run = current_time + timedelta(days=1)
        elif frequency == ScheduleFrequency.WEEKLY:
            next_run = current_time + timedelta(weeks=1)
        elif frequency == ScheduleFrequency.MONTHLY:
            next_run = current_time + timedelta(days=30)
        else:
            next_run = current_time
        
        schedule = TrainingSchedule(
            schedule_id=schedule_id,
            model_id=model_id,
            model_type=model_type,
            frequency=frequency,
            enabled=True,
            next_run=next_run,
            last_run=None,
            parameters=parameters or {},
            created_at=current_time,
            updated_at=current_time
        )
        
        self.schedules[schedule_id] = schedule
        
        logger.info("创建训练调度", 
                   schedule_id=schedule_id,
                   model_id=model_id,
                   frequency=frequency.value)
        
        return schedule_id
    
    def update_schedule(self, schedule_id: str, 
                       frequency: Optional[ScheduleFrequency] = None,
                       parameters: Optional[Dict[str, Any]] = None,
                       enabled: Optional[bool] = None) -> bool:
        """Update an existing training schedule"""
        if schedule_id not in self.schedules:
            return False
        
        schedule = self.schedules[schedule_id]
        
        if frequency:
            schedule.frequency = frequency
        
        if parameters:
            schedule.parameters.update(parameters)
        
        if enabled is not None:
            schedule.enabled = enabled
        
        schedule.updated_at = datetime.now(timezone.utc)
        
        logger.info("更新训练调度", schedule_id=schedule_id)
        return True
    
    def delete_schedule(self, schedule_id: str) -> bool:
        """Delete a training schedule"""
        if schedule_id not in self.schedules:
            return False
        
        # Cancel any running jobs for this schedule
        for job in list(self.active_jobs.values()):
            if job.schedule_id == schedule_id:
                asyncio.create_task(self._cancel_job(job.job_id))
        
        del self.schedules[schedule_id]
        
        logger.info("删除训练调度", schedule_id=schedule_id)
        return True
    
    def get_schedule_status(self, schedule_id: str) -> Optional[Dict[str, Any]]:
        """Get schedule status and recent jobs"""
        if schedule_id not in self.schedules:
            return None
        
        schedule = self.schedules[schedule_id]
        
        # Get recent jobs for this schedule
        recent_jobs = []
        for job in self.jobs.values():
            if job.schedule_id == schedule_id:
                recent_jobs.append({
                    "job_id": job.job_id,
                    "status": job.status.value,
                    "started_at": job.started_at.isoformat(),
                    "completed_at": job.completed_at.isoformat() if job.completed_at else None,
                    "progress": float(job.progress),
                    "error": job.error
                })
        
        # Sort by start time (most recent first)
        recent_jobs.sort(key=lambda x: x["started_at"], reverse=True)
        recent_jobs = recent_jobs[:10]  # Keep last 10 jobs
        
        return {
            "schedule": {
                "schedule_id": schedule.schedule_id,
                "model_id": schedule.model_id,
                "model_type": schedule.model_type,
                "frequency": schedule.frequency.value,
                "enabled": schedule.enabled,
                "next_run": schedule.next_run.isoformat(),
                "last_run": schedule.last_run.isoformat() if schedule.last_run else None,
                "parameters": schedule.parameters,
                "created_at": schedule.created_at.isoformat(),
                "updated_at": schedule.updated_at.isoformat()
            },
            "recent_jobs": recent_jobs,
            "active_job_count": len([j for j in recent_jobs if j["status"] == "running"])
        }
    
    def get_all_schedules(self) -> List[Dict[str, Any]]:
        """Get all schedules with status"""
        return [self.get_schedule_status(sid) for sid in self.schedules.keys()]
    
    def get_job_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get job status"""
        if job_id not in self.jobs:
            return None
        
        job = self.jobs[job_id]
        
        return {
            "job_id": job.job_id,
            "schedule_id": job.schedule_id,
            "model_id": job.model_id,
            "status": job.status.value,
            "started_at": job.started_at.isoformat(),
            "completed_at": job.completed_at.isoformat() if job.completed_at else None,
            "progress": float(job.progress),
            "result": job.result,
            "error": job.error,
            "metadata": job.metadata
        }
    
    def get_all_jobs(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get all jobs with optional limit"""
        jobs_list = list(self.jobs.values())
        jobs_list.sort(key=lambda x: x.started_at, reverse=True)
        return [self.get_job_status(j.job_id) for j in jobs_list[:limit]]
    
    def add_job_start_callback(self, callback: Callable):
        """Add callback for job start events"""
        self.job_start_callbacks.append(callback)
    
    def add_job_complete_callback(self, callback: Callable):
        """Add callback for job completion events"""
        self.job_complete_callbacks.append(callback)
    
    def add_job_error_callback(self, callback: Callable):
        """Add callback for job error events"""
        self.job_error_callbacks.append(callback)
    
    async def run_on_demand_training(self, model_id: str, model_type: str,
                                   training_data: List[Dict[str, Any]],
                                   parameters: Dict[str, Any] = None) -> str:
        """Run on-demand training"""
        job_id = f"ondemand_{model_id}_{int(datetime.now().timestamp())}"
        
        # Create schedule for this on-demand job
        schedule_id = f"ondemand_sched_{int(datetime.now().timestamp())}"
        
        schedule = TrainingSchedule(
            schedule_id=schedule_id,
            model_id=model_id,
            model_type=model_type,
            frequency=ScheduleFrequency.ON_DEMAND,
            enabled=True,
            next_run=datetime.now(timezone.utc),
            last_run=None,
            parameters=parameters or {},
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        
        self.schedules[schedule_id] = schedule
        
        # Create job
        job = TrainingJob(
            job_id=job_id,
            schedule_id=schedule_id,
            model_id=model_id,
            status=TrainingStatus.SCHEDULED,
            started_at=datetime.now(timezone.utc),
            completed_at=None,
            progress=Decimal("0.0"),
            result=None,
            error=None,
            metadata={"training_data_size": len(training_data)}
        )
        
        self.jobs[job_id] = job
        self.active_jobs[job_id] = job
        
        # Execute immediately
        asyncio.create_task(self._run_on_demand_training_job(job, training_data))
        
        logger.info("开始按需训练", 
                   job_id=job_id,
                   model_id=model_id,
                   data_size=len(training_data))
        
        return job_id
    
    async def _run_on_demand_training_job(self, job: TrainingJob, training_data: List[Dict[str, Any]]):
        """Run on-demand training job"""
        try:
            job.status = TrainingStatus.RUNNING
            await self._notify_job_start(job)
            
            job.progress = Decimal("0.2")
            
            # Train model
            training_result = await self.model_trainer.train_model(
                model_id=job.model_id,
                training_data=training_data,
                training_config=job.metadata
            )
            
            job.progress = Decimal("0.9")
            
            job.status = TrainingStatus.COMPLETED
            job.completed_at = datetime.now(timezone.utc)
            job.progress = Decimal("1.0")
            job.result = training_result
            
            await self._notify_job_complete(job)
            
        except Exception as e:
            logger.error("按需训练失败", 
                        job_id=job.job_id,
                        error=str(e))
            
            job.status = TrainingStatus.FAILED
            job.completed_at = datetime.now(timezone.utc)
            job.error = str(e)
            
            await self._notify_job_error(job, e)
        
        finally:
            if job.job_id in self.active_jobs:
                del self.active_jobs[job.job_id]
        
        # Clean up on-demand schedule
        if job.schedule_id in self.schedules:
            del self.schedules[job.schedule_id]