import fitz  # PyMuPDF
import os
from django.conf import settings
from grading.models import Annotation, Score
from exams.models import Copy

class PDFFlattener:
    """
    Service pour aplatir les annotations et générer le rendu final du PDF.
    """

    def float_or_zero(self, val):
        try:
           return float(val)
        except:
           return 0.0

    def flatten_copy(self, copy: Copy):
        """
        Génère un PDF final pour la copie donnée.
        1. Crée un nouveau PDF.
        2. Ajoute chaque page (image) du fascicule.
        3. Dessine les traits rouges (Annotations).
        4. Ajoute une page de garde avec le tableau des notes.
        5. Sauvegarde et met à jour copy.final_pdf.
        """
        
        doc = fitz.open()
        
        # 0. Récupérer les images des pages.
        # copy.booklets est ManyToMany. Pour MVP on suppose 1 seul booklet ou on les concatène.
        # On itère sur les booklets assignés.
        all_pages_images = []
        for booklet in copy.booklets.all().order_by('start_page'):
            if booklet.pages_images:
                 all_pages_images.extend(booklet.pages_images)
        
        # S'assurer d'avoir des images
        if not all_pages_images:
            # Fallback ou erreur. Pour MVP on skip si vide.
            print(f"Copy {copy.id} has no pages to flatten.")
            return

        # 1. & 2. Ajouter pages et dessiner
        # Charger les annotations
        annotations = list(copy.annotations.all())
        
        # Échelle: Le PDF créé à partir d'une image prend la dimension de l'image.
        # CanvasLayer enregistre des coordonnées pixels par rapport à l'image affichée.
        # Si on affiche l'image brute, coordonnée canvas = coordonnée image (si scale 1).
        # On a passé `pdfDimensions` au CanvasLayer.
        # Supposons que les annotations sont stockées en coordonnées absolues de l'image source.
        # Si ce n'est pas le cas, il faudra une conversion.
        # Hypothèse MVP: Frontend envoie coords relatives à la résolution d'affichage (ex: width=800).
        # Backend doit savoir quelle était cette résolution ou normaliser (0-1).
        # Pour ce MVP, on va assumer que l'image insérée fait la même taille que le canvas ou scaler.
        
        for idx, img_path in enumerate(all_pages_images):
            # img_path est relatif ou absolu ? `pages_images` stocke quoi ?
            # `Splitter` retourne des chemins ou des bytes ?
            # Dans `Splitter` (placeholder), on n'a pas défini le stockage.
            # Supposons que ce sont des chemins absolus ou relatifs à MEDIA_ROOT.
            full_path = str(settings.MEDIA_ROOT / img_path) if not img_path.startswith('/') else img_path
            
            if not os.path.exists(full_path):
                continue
                
            img = fitz.open(full_path)
            rect = img[0].rect
            pdfbytes = img.convert_to_pdf()
            img.close()
            
            img_pdf = fitz.open("pdf", pdfbytes)
            page = doc.new_page(width = rect.width, height = rect.height)
            page.show_pdf_page(rect, img_pdf, 0)
            
            # Dessiner les annotations pour cette page (idx + 1 car page_number est souvent 1-based)
            page_annotations = [a for a in annotations if a.page_number == idx + 1]
            
            shape = page.new_shape()
            shape.draw_rect(rect) # Context ?
            
            # CanvasLayer saves: [{type: 'path', color: 'red', points: [{x,y}, {x,y}]}]
            for annot in page_annotations:
                data = annot.vector_data
                # data est une liste d'objets path
                if isinstance(data, list):
                   for item in data:
                       if item.get('type') == 'path' and 'points' in item:
                           points = item['points']
                           if len(points) > 1:
                               # Start path
                               p0 = points[0]
                               shape.draw_line(fitz.Point(p0['x'], p0['y']), fitz.Point(p0['x'], p0['y'])) # Start point
                               # Il faut faire un moveTo, lineTo. fitz Shape API:
                               # finish() non, draw_polyline
                               pd_points = [fitz.Point(p['x'], p['y']) for p in points]
                               shape.draw_polyline(pd_points)
                               shape.finish(color=(1, 0, 0), width=2) # Red stroke
            
            shape.commit()

        # 3. Page de garde (Summary)
        summary_page = doc.new_page(width=595, height=842) # A4
        text_writer = fitz.TextWriter(summary_page.rect)
        
        # Titre
        text_writer.append(fitz.Point(50, 50), "Relevé de Notes", fontsize=24)
        
        # Récupérer les scores
        score_obj = copy.scores.first()
        scores_data = score_obj.scores_data if score_obj else {}
        
        y = 100
        total = 0
        for key, val in scores_data.items():
            val_float = self.float_or_zero(val)
            total += val_float
            text_writer.append(fitz.Point(50, y), f"{key} : {val_float}", fontsize=12)
            y += 20
        
        text_writer.append(fitz.Point(50, y + 20), f"TOTAL : {total}", fontsize=16)
        text_writer.write_text(summary_page)
        
        # 4. Sauvegarder
        output_filename = f"copy_{copy.id}_corrected.pdf"
        output_path = settings.MEDIA_ROOT / "corrected" / output_filename
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        doc.save(str(output_path))
        doc.close()

        # 5. Mettre à jour copy.final_pdf
        from django.core.files import File
        relative_path = f"corrected/{output_filename}"

        with open(str(output_path), 'rb') as pdf_file:
            copy.final_pdf.save(output_filename, File(pdf_file), save=False)

        copy.status = Copy.Status.GRADED
        copy.save()

        print(f"Copy {copy.id} flattened successfully: {relative_path}")

