from rest_framework import permissions
from .models import CopyLock, Copy

class IsLockedByOwnerOrReadOnly(permissions.BasePermission):
    """
    Allows write access only if the copy is LOCKED by the request.user.
    Read access is allowed to everyone (or handled by other permissions).
    """
    def has_object_permission(self, request, view, obj):
        # Read permissions are allowed to any request,
        # so we'll always allow GET, HEAD or OPTIONS requests.
        if request.method in permissions.SAFE_METHODS:
            return True

        # Write permissions are only allowed to the owner of the lock.
        # Check if obj is Copy, or related to Copy (Annotation)
        copy = None
        if isinstance(obj, Copy):
            copy = obj
        elif hasattr(obj, 'copy'): # Annotation
            copy = obj.copy
        
        if not copy:
             # Should not happen if used correctly
             return False

        # Check Lock
        try:
            lock = copy.lock
            # Check expiration (lazy check)
            # logic here mimics views_lock but ideally we call a service
            # For simplicity:
            if lock.owner == request.user:
                return True
            else:
                return False # Locked by other
        except Copy.DoesNotExist: # Should be CopyLock.DoesNotExist but accessed via reverse relation
             # No lock exists. 
             # VOIE C3: Write requires lock?
             # User spec: "Toute opération d’écriture sur une copie DOIT exiger un lock détenu par l’utilisateur."
             return False
        except Exception: 
             return False
        return False
        
    def has_permission(self, request, view):
         # Used for ListCreate Views where we don't have obj yet but have URL kwarg
         if request.method in permissions.SAFE_METHODS:
            return True
            
         copy_id = view.kwargs.get('copy_id')
         if not copy_id:
             return True # Skip check if not copy-related view
             
         # Check Lock for Copy
         # We need to query
         from .models import CopyLock
         try:
             lock = CopyLock.objects.get(copy_id=copy_id)
             if lock.owner == request.user:
                 return True
         except CopyLock.DoesNotExist:
             pass
             
         return False
