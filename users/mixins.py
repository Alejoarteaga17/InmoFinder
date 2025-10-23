from django.core.exceptions import PermissionDenied
from django.contrib.auth.mixins import LoginRequiredMixin

class AdminRequiredMixin(LoginRequiredMixin):
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return super().dispatch(request, *args, **kwargs)  # redirige a login por LoginRequiredMixin
        if not getattr(request.user, "is_admin", False):
            raise PermissionDenied("ADMIN_ONLY")
        return super().dispatch(request, *args, **kwargs)

class PropietarioRequiredMixin(LoginRequiredMixin):
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return super().dispatch(request, *args, **kwargs)
        if not getattr(request.user, "is_propietario", False):
            raise PermissionDenied("PROPIETARIO_ONLY")
        return super().dispatch(request, *args, **kwargs)

class CompradorRequiredMixin(LoginRequiredMixin):
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return super().dispatch(request, *args, **kwargs)
        if not getattr(request.user, "is_comprador", False):
            raise PermissionDenied("COMPRADOR_ONLY")
        return super().dispatch(request, *args, **kwargs)

class OwnerOrAdminObjectMixin(LoginRequiredMixin):
    """
    Para vistas que operan sobre un objeto con campo 'owner'.
    """
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return super().dispatch(request, *args, **kwargs)
        obj = self.get_object()
        if getattr(request.user, "is_admin", False):
            return super().dispatch(request, *args, **kwargs)
        if getattr(obj, "owner_id", None) != request.user.id:
            raise PermissionDenied("OWNER_ONLY")
        return super().dispatch(request, *args, **kwargs)
