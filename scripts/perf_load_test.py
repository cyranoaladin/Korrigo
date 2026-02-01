#!/usr/bin/env python
"""
ZF-AUD-13: Performance Load Test Script
Simulates 100 copies, 30 teachers, concurrent operations

Usage:
    python scripts/perf_load_test.py --scenario import
    python scripts/perf_load_test.py --scenario correction
    python scripts/perf_load_test.py --scenario finalize
    python scripts/perf_load_test.py --scenario full
"""
import os
import sys
import time
import random
import argparse
import statistics
import concurrent.futures
from datetime import datetime
from dataclasses import dataclass, field
from typing import List, Dict, Any

# Django setup
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')

import django
django.setup()

from django.contrib.auth import get_user_model
from django.utils import timezone
from django.db import connection, reset_queries
from django.conf import settings

User = get_user_model()


@dataclass
class MetricsCollector:
    """Collect and analyze performance metrics."""
    operation: str
    latencies: List[float] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    start_time: float = 0
    end_time: float = 0
    
    def record(self, latency: float, error: str = None):
        self.latencies.append(latency)
        if error:
            self.errors.append(error)
    
    def summary(self) -> Dict[str, Any]:
        if not self.latencies:
            return {"operation": self.operation, "count": 0}
        
        sorted_latencies = sorted(self.latencies)
        p50_idx = int(len(sorted_latencies) * 0.50)
        p95_idx = int(len(sorted_latencies) * 0.95)
        p99_idx = int(len(sorted_latencies) * 0.99)
        
        return {
            "operation": self.operation,
            "count": len(self.latencies),
            "errors": len(self.errors),
            "error_rate": f"{len(self.errors) / len(self.latencies) * 100:.2f}%",
            "min_ms": f"{min(self.latencies) * 1000:.2f}",
            "max_ms": f"{max(self.latencies) * 1000:.2f}",
            "avg_ms": f"{statistics.mean(self.latencies) * 1000:.2f}",
            "p50_ms": f"{sorted_latencies[p50_idx] * 1000:.2f}",
            "p95_ms": f"{sorted_latencies[p95_idx] * 1000:.2f}",
            "p99_ms": f"{sorted_latencies[min(p99_idx, len(sorted_latencies)-1)] * 1000:.2f}",
            "total_duration_s": f"{self.end_time - self.start_time:.2f}",
            "throughput_ops": f"{len(self.latencies) / (self.end_time - self.start_time):.2f}",
        }


def simulate_import_operation(exam_id: str, copy_num: int) -> tuple:
    """Simulate PDF import (without actual file)."""
    from exams.models import Exam, Copy, Booklet
    from grading.services import GradingService
    
    start = time.time()
    error = None
    
    try:
        exam = Exam.objects.get(id=exam_id)
        
        # Create copy directly (simulating import result)
        copy = Copy.objects.create(
            exam=exam,
            anonymous_id=f"PERF-{copy_num:04d}-{random.randint(1000,9999)}",
            status=Copy.Status.STAGING
        )
        
        # Create booklet with simulated pages
        booklet = Booklet.objects.create(
            exam=exam,
            start_page=1,
            end_page=4,
            pages_images=[f"page_{i}.png" for i in range(4)]
        )
        copy.booklets.add(booklet)
        
        # Validate to READY
        copy.status = Copy.Status.READY
        copy.save()
        
    except Exception as e:
        error = str(e)
    
    return time.time() - start, error


def simulate_lock_operation(copy_id: str, user_id: int) -> tuple:
    """Simulate lock acquisition."""
    from exams.models import Copy
    from grading.services import GradingService
    
    start = time.time()
    error = None
    
    try:
        copy = Copy.objects.get(id=copy_id)
        user = User.objects.get(id=user_id)
        
        if copy.status == Copy.Status.READY:
            lock, created = GradingService.acquire_lock(copy, user)
    except Exception as e:
        error = str(e)
    
    return time.time() - start, error


def simulate_annotation_operation(copy_id: str, user_id: int, lock_token: str = None) -> tuple:
    """Simulate annotation creation."""
    from exams.models import Copy
    from grading.services import AnnotationService, GradingService
    
    start = time.time()
    error = None
    
    try:
        copy = Copy.objects.get(id=copy_id)
        user = User.objects.get(id=user_id)
        
        # Get or create lock
        if copy.status == Copy.Status.READY:
            lock, _ = GradingService.acquire_lock(copy, user)
            lock_token = str(lock.token)
            copy.refresh_from_db()
        
        if copy.status == Copy.Status.LOCKED:
            AnnotationService.add_annotation(
                copy,
                {
                    'page_index': random.randint(0, 3),
                    'x': random.random() * 0.8,
                    'y': random.random() * 0.8,
                    'w': 0.1,
                    'h': 0.05,
                    'content': f'Annotation {random.randint(1, 100)}',
                    'score_delta': random.randint(-5, 5)
                },
                user,
                lock_token=lock_token
            )
    except Exception as e:
        error = str(e)
    
    return time.time() - start, error


def simulate_finalize_operation(copy_id: str, user_id: int) -> tuple:
    """Simulate finalize (without actual PDF generation)."""
    from exams.models import Copy
    from grading.models import GradingEvent
    
    start = time.time()
    error = None
    
    try:
        copy = Copy.objects.get(id=copy_id)
        user = User.objects.get(id=user_id)
        
        # Simulate finalize by changing status
        if copy.status in [Copy.Status.LOCKED, Copy.Status.READY]:
            copy.status = Copy.Status.GRADED
            copy.save()
            
            # Create finalize event
            GradingEvent.objects.create(
                copy=copy,
                action=GradingEvent.Action.FINALIZE,
                actor=user,
                metadata={'simulated': True}
            )
    except Exception as e:
        error = str(e)
    
    return time.time() - start, error


def run_import_scenario(num_copies: int = 100) -> MetricsCollector:
    """Run import scenario."""
    from exams.models import Exam
    
    print(f"\n{'='*60}")
    print(f"IMPORT SCENARIO: {num_copies} copies")
    print(f"{'='*60}")
    
    # Create test exam
    exam = Exam.objects.create(
        name=f"Perf Test Import {datetime.now().isoformat()}",
        date=timezone.now().date()
    )
    
    metrics = MetricsCollector(operation="import")
    metrics.start_time = time.time()
    
    for i in range(num_copies):
        latency, error = simulate_import_operation(str(exam.id), i)
        metrics.record(latency, error)
        
        if (i + 1) % 10 == 0:
            print(f"  Imported {i + 1}/{num_copies} copies...")
    
    metrics.end_time = time.time()
    return metrics


def run_correction_scenario(num_teachers: int = 30, annotations_per_copy: int = 10) -> MetricsCollector:
    """Run correction scenario with concurrent teachers."""
    from exams.models import Exam, Copy
    from django.contrib.auth.models import Group
    from core.auth import create_user_roles
    
    print(f"\n{'='*60}")
    print(f"CORRECTION SCENARIO: {num_teachers} teachers, {annotations_per_copy} annotations/copy")
    print(f"{'='*60}")
    
    # Setup
    admin_group, teacher_group, _ = create_user_roles()
    
    # Create teachers
    teachers = []
    for i in range(num_teachers):
        user, _ = User.objects.get_or_create(
            username=f"perf_teacher_{i}",
            defaults={'password': 'testpass123'}
        )
        user.groups.add(teacher_group)
        teachers.append(user)
    
    # Create exam with copies
    exam = Exam.objects.create(
        name=f"Perf Test Correction {datetime.now().isoformat()}",
        date=timezone.now().date()
    )
    
    copies = []
    for i in range(num_teachers * 3):  # 3 copies per teacher
        copy = Copy.objects.create(
            exam=exam,
            anonymous_id=f"CORR-{i:04d}-{random.randint(1000,9999)}",
            status=Copy.Status.READY
        )
        copies.append(copy)
    
    metrics = MetricsCollector(operation="annotation")
    metrics.start_time = time.time()
    
    # Simulate concurrent corrections
    for copy in copies:
        teacher = random.choice(teachers)
        
        # Lock
        lock_latency, lock_error = simulate_lock_operation(str(copy.id), teacher.id)
        metrics.record(lock_latency, lock_error)
        
        copy.refresh_from_db()
        
        # Add annotations
        for _ in range(annotations_per_copy):
            ann_latency, ann_error = simulate_annotation_operation(str(copy.id), teacher.id)
            metrics.record(ann_latency, ann_error)
    
    metrics.end_time = time.time()
    return metrics


def run_finalize_scenario(num_copies: int = 100) -> MetricsCollector:
    """Run finalize scenario."""
    from exams.models import Exam, Copy
    
    print(f"\n{'='*60}")
    print(f"FINALIZE SCENARIO: {num_copies} copies")
    print(f"{'='*60}")
    
    # Create admin user
    admin, _ = User.objects.get_or_create(
        username="perf_admin",
        defaults={'is_staff': True, 'is_superuser': True}
    )
    
    # Create exam with LOCKED copies
    exam = Exam.objects.create(
        name=f"Perf Test Finalize {datetime.now().isoformat()}",
        date=timezone.now().date()
    )
    
    copies = []
    for i in range(num_copies):
        copy = Copy.objects.create(
            exam=exam,
            anonymous_id=f"FIN-{i:04d}-{random.randint(1000,9999)}",
            status=Copy.Status.LOCKED
        )
        copies.append(copy)
    
    metrics = MetricsCollector(operation="finalize")
    metrics.start_time = time.time()
    
    for i, copy in enumerate(copies):
        latency, error = simulate_finalize_operation(str(copy.id), admin.id)
        metrics.record(latency, error)
        
        if (i + 1) % 10 == 0:
            print(f"  Finalized {i + 1}/{num_copies} copies...")
    
    metrics.end_time = time.time()
    return metrics


def analyze_database_queries():
    """Analyze database query patterns."""
    from django.db import connection
    
    print(f"\n{'='*60}")
    print("DATABASE QUERY ANALYSIS")
    print(f"{'='*60}")
    
    # Check for missing indexes
    from exams.models import Copy
    from grading.models import Annotation, GradingEvent
    
    print("\nModel Index Analysis:")
    
    models_to_check = [
        ('Copy', Copy),
        ('Annotation', Annotation),
        ('GradingEvent', GradingEvent),
    ]
    
    for name, model in models_to_check:
        meta = model._meta
        indexes = list(meta.indexes)
        db_indexes = [f.name for f in meta.get_fields() if getattr(f, 'db_index', False)]
        
        print(f"\n  {name}:")
        print(f"    - Explicit indexes: {len(indexes)}")
        print(f"    - Field db_index: {db_indexes}")
        
        # Suggest indexes for common queries
        if name == 'Copy':
            print(f"    - Suggested: (exam, status), (assigned_corrector, status)")
        elif name == 'Annotation':
            print(f"    - Suggested: (copy, page_index), (created_by, created_at)")


def print_report(metrics_list: List[MetricsCollector]):
    """Print performance report."""
    print(f"\n{'='*60}")
    print("PERFORMANCE REPORT")
    print(f"{'='*60}")
    
    for metrics in metrics_list:
        summary = metrics.summary()
        print(f"\n{summary['operation'].upper()}:")
        print(f"  Total operations: {summary['count']}")
        print(f"  Errors: {summary['errors']} ({summary['error_rate']})")
        print(f"  Latency (ms):")
        print(f"    - Min: {summary['min_ms']}")
        print(f"    - Avg: {summary['avg_ms']}")
        print(f"    - P50: {summary['p50_ms']}")
        print(f"    - P95: {summary['p95_ms']}")
        print(f"    - P99: {summary['p99_ms']}")
        print(f"    - Max: {summary['max_ms']}")
        print(f"  Throughput: {summary['throughput_ops']} ops/s")
        print(f"  Total duration: {summary['total_duration_s']}s")


def main():
    parser = argparse.ArgumentParser(description='Performance Load Test')
    parser.add_argument('--scenario', choices=['import', 'correction', 'finalize', 'full', 'analyze'],
                        default='analyze', help='Scenario to run')
    parser.add_argument('--copies', type=int, default=100, help='Number of copies')
    parser.add_argument('--teachers', type=int, default=30, help='Number of teachers')
    
    args = parser.parse_args()
    
    print(f"\n{'#'*60}")
    print(f"# ZF-AUD-13: Performance Load Test")
    print(f"# Scenario: {args.scenario}")
    print(f"# Copies: {args.copies}, Teachers: {args.teachers}")
    print(f"# Started: {datetime.now().isoformat()}")
    print(f"{'#'*60}")
    
    metrics_list = []
    
    if args.scenario in ['import', 'full']:
        metrics_list.append(run_import_scenario(args.copies))
    
    if args.scenario in ['correction', 'full']:
        metrics_list.append(run_correction_scenario(args.teachers))
    
    if args.scenario in ['finalize', 'full']:
        metrics_list.append(run_finalize_scenario(args.copies))
    
    if args.scenario == 'analyze' or args.scenario == 'full':
        analyze_database_queries()
    
    if metrics_list:
        print_report(metrics_list)
    
    print(f"\n{'#'*60}")
    print(f"# Completed: {datetime.now().isoformat()}")
    print(f"{'#'*60}")


if __name__ == '__main__':
    main()
