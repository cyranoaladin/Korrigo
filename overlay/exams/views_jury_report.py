"""
Views pour servir les rapports de jury statiques (fichiers markdown)
"""
import os
from django.conf import settings
from django.http import HttpResponse, Http404
from django.views import View
from rest_framework.permissions import IsAuthenticated


class StaticJuryReportView(View):
    """
    GET /api/exams/jury-report/stat_BB_MATHS_2026/
    Sert le rapport de jury statique du Bac Blanc Maths 2026
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, filename):
        """
        Sert un fichier markdown de rapport de jury statique
        """
        # Liste des fichiers de rapports autorisés
        allowed_reports = ['stat_BB_MATHS_2026.md']
        
        if filename not in allowed_reports:
            raise Http404("Rapport non trouvé")
        
        # Chemin vers le fichier - chercher d'abord dans l'overlay, sinon dans BASE_DIR.parent
        overlay_path = os.path.join('/app', filename)
        base_path = os.path.join(settings.BASE_DIR.parent, filename)
        
        # Priorité : overlay > BASE_DIR.parent
        file_path = overlay_path if os.path.exists(overlay_path) else base_path
        
        if not os.path.exists(file_path):
            raise Http404("Fichier non trouvé")
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            response = HttpResponse(content.encode('utf-8'), content_type='text/markdown; charset=utf-8')
            response['Content-Disposition'] = f'inline; filename="{filename}"'
            return response
        except Exception as e:
            raise Http404(f"Erreur lors de la lecture du fichier: {e}")
