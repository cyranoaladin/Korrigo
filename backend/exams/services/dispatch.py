from typing import List, Dict
import random
from django.db import transaction
from django.utils import timezone
from exams.models import Exam, Copy
from django.contrib.auth import get_user_model

User = get_user_model()

class DispatchService:
    """
    Service to dispatch copies equitably and randomly among assigned correctors.
    """

    @staticmethod
    def dispatch_copies(exam: Exam) -> Dict[str, int]:
        """
        Dispatches all READY copies of an exam to its assigned correctors.
        
        Algorithm:
        1. Fetch all copies with status READY (or higher if re-dispatching?)
           - Usually dispatch happens once on READY copies.
        2. Fetch all correctors assigned to the exam.
        3. Shuffle copies randomly.
        4. Distribute round-robin to ensure even split.
        
        Returns:
            Dict showing count of copies assigned per corrector username.
        """
        correctors = list(exam.correctors.all())
        if not correctors:
            raise ValueError("No correctors assigned to this exam.")

        # Filter actionable copies (READY)
        # We might want to include STAGING if auto-dispatch is requested early, 
        # but safely we should dispatch only validated copies.
        copies = list(exam.copies.filter(
            status__in=[Copy.Status.READY, Copy.Status.STAGING], # Allow STAGING if we want early dispatch
            assigned_corrector__isnull=True
        ))
        
        if not copies:
            return {"message": "No unassigned copies to dispatch."}

        # Randomize
        random.shuffle(copies)
        random.shuffle(correctors) # Randomize starting corrector too

        # Round-robin assignment
        assignments = {c.username: 0 for c in correctors}
        corrector_count = len(correctors)
        
        copies_to_update = []
        import uuid
        dispatch_id = uuid.uuid4()
        now = timezone.now()

        for idx, copy in enumerate(copies):
            corrector = correctors[idx % corrector_count]
            
            copy.assigned_corrector = corrector
            copy.dispatch_run_id = dispatch_id
            copy.assigned_at = now
            # If copy was STAGING, should we move to READY? 
            # Ideally dispatch doesn't change validation status, only assignment.
            
            copies_to_update.append(copy)
            assignments[corrector.username] += 1
            
        # Bulk update for performance
        with transaction.atomic():
            Copy.objects.bulk_update(copies_to_update, ['assigned_corrector', 'dispatch_run_id', 'assigned_at'])
            
        return assignments
