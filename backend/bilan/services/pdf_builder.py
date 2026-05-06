"""
PDF Builder for DNB Bilan Reports

Creates formatted PDF reports from JSON data.
"""

from datetime import datetime
from typing import Dict, Any
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.colors import black, blue, red, green
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.platypus import PageBreak
import io


class BilanPDFBuilder:
    """
    Builds PDF reports from DNB bilan data.
    """

    def __init__(self):
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()

    def _setup_custom_styles(self):
        """Configure custom styles for the report."""
        # Title style
        self.styles.add(ParagraphStyle(
            name='CustomTitle',
            parent=self.styles['Heading1'],
            fontSize=16,
            spaceAfter=20,
            alignment=1,  # Center
            textColor=black,
        ))

        # Section header
        self.styles.add(ParagraphStyle(
            name='SectionHeader',
            parent=self.styles['Heading2'],
            fontSize=14,
            spaceAfter=12,
            spaceBefore=20,
            textColor=blue,
        ))

        # Subsection
        self.styles.add(ParagraphStyle(
            name='Subsection',
            parent=self.styles['Heading3'],
            fontSize=12,
            spaceAfter=8,
            spaceBefore=12,
        ))

        # Body text
        self.styles.add(ParagraphStyle(
            name='BodyText',
            parent=self.styles['Normal'],
            fontSize=10,
            spaceAfter=6,
            leading=14,
        ))

    def build(self, bilan_data: Dict[str, Any]) -> str:
        """
        Build PDF from bilan data.
        Returns the file path.
        """
        # Create PDF buffer
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=72,
            leftMargin=72,
            topMargin=72,
            bottomMargin=18
        )

        # Build story
        story = []

        # Title page
        story.extend(self._build_title_page(bilan_data))
        story.append(PageBreak())

        # Section 1: Statistics
        story.extend(self._build_section_stats(bilan_data['s1_stats']))

        # Section 2: Domains
        story.extend(self._build_section_domains(bilan_data['s2_domains']))

        # Section 3: Questions
        story.extend(self._build_section_questions(bilan_data['s3_questions']))

        # Section 4: Competences
        story.extend(self._build_section_competences(bilan_data['s4_competences']))

        # Section 5: Correctors (if admin)
        if bilan_data.get('s5_correctors', {}).get('data'):
            story.extend(self._build_section_correctors(bilan_data['s5_correctors']))

        # Section 6: Profiles
        story.extend(self._build_section_profiles(bilan_data['s6_profiles']))

        # Section 7: Recommendations
        story.extend(self._build_section_recommendations(bilan_data['s7_recommendations']))

        # Build PDF
        doc.build(story)

        # Save to file
        buffer.seek(0)
        filename = f"bilan_dnb_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        
        # For now, return the buffer content
        # In production, this would be saved to media storage
        return buffer.getvalue()

    def _build_title_page(self, bilan_data: Dict[str, Any]) -> list:
        """Build the title page."""
        story = []
        metadata = bilan_data['metadata']

        # Main title
        story.append(Paragraph("BILAN PÉDAGOGIQUE DNB 2026", self.styles['CustomTitle']))
        story.append(Spacer(1, 20))

        # Subtitle
        story.append(Paragraph(
            f"Mathématiques — {metadata['n_copies']} copies analysées",
            self.styles['Heading2']
        ))
        story.append(Spacer(1, 30))

        # Metadata table
        meta_data = [
            ['Date de génération:', metadata['generated_at'][:10]],
            ['Modèles LLM:', metadata['llm_model']],
            ['Collection RAG:', metadata['rag_collection']],
            ['Temps de génération:', f"{metadata['generation_time_seconds']:.1f}s"],
        ]

        meta_table = Table(meta_data, colWidths=[2*inch, 4*inch])
        meta_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), '#f0f0f0'),
            ('TEXTCOLOR', (0, 0), (-1, -1), black),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('GRID', (0, 0), (-1, -1), 1, black),
        ]))

        story.append(meta_table)
        story.append(Spacer(1, 50))

        return story

    def _build_section_stats(self, stats: Dict[str, Any]) -> list:
        """Build Section 1: Statistics."""
        story = []
        
        story.append(Paragraph("SECTION 1 — TABLEAU DE BORD STATISTIQUE", self.styles['SectionHeader']))

        # Key indicators
        indicators = [
            ['Nombre de copies:', str(stats['n_copies'])],
            ['Moyenne:', f"{stats['mean']}/20"],
            ['Médiane:', f"{stats['median']}/20"],
            ['Écart-type:', f"{stats['std']}"],
            ['Note minimale:', str(stats['min'])],
            ['Note maximale:', str(stats['max'])],
            ['Taux réussite ≥10:', f"{stats['pct_above_10']}%"],
        ]

        indicators_table = Table(indicators, colWidths=[2.5*inch, 1.5*inch])
        indicators_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), '#e0e0e0'),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('GRID', (0, 0), (-1, -1), 1, black),
        ]))

        story.append(indicators_table)
        story.append(Spacer(1, 20))

        # Mentions distribution
        if 'mentions' in stats:
            story.append(Paragraph("Répartition par mentions:", self.styles['Subsection']))
            
            mentions_data = [['Mention', 'Effectif', '%']]
            for mention, count in stats['mentions'].items():
                percentage = (count / stats['n_copies']) * 100
                mentions_data.append([mention, str(count), f"{percentage:.1f}%"])

            mentions_table = Table(mentions_data, colWidths=[1.5*inch, 1*inch, 1*inch])
            mentions_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), '#d0d0d0'),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('GRID', (0, 0), (-1, -1), 1, black),
            ]))

            story.append(mentions_table)

        return story

    def _build_section_domains(self, domains_data: Dict[str, Any]) -> list:
        """Build Section 2: Domain analysis."""
        story = []
        
        story.append(Paragraph("SECTION 2 — ANALYSE PAR DOMAINE", self.styles['SectionHeader']))

        # Domain performance table
        domain_stats = domains_data['data']
        sorted_domains = sorted(domain_stats.items(), key=lambda x: x[1], reverse=True)
        
        table_data = [['Domaine', 'Taux réussite', 'Signal']]
        for domain, rate in sorted_domains:
            if rate >= 70:
                signal = "✓ Vert"
                color = green
            elif rate >= 40:
                signal = "⚠ Orange"
                color = 'orange'
            else:
                signal = "✗ Rouge"
                color = red
            table_data.append([domain, f"{rate}%", signal])

        domain_table = Table(table_data, colWidths=[2*inch, 1.5*inch, 1.5*inch])
        domain_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), '#d0d0d0'),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('GRID', (0, 0), (-1, -1), 1, black),
        ]))

        story.append(domain_table)
        story.append(Spacer(1, 20))

        # LLM analyses
        analyses = domains_data.get('analyses', {})
        for domain, analysis in analyses.items():
            story.append(Paragraph(f"Analyse — {domain}:", self.styles['Subsection']))
            story.append(Paragraph(analysis, self.styles['BodyText']))
            story.append(Spacer(1, 12))

        return story

    def _build_section_questions(self, questions_data: list) -> list:
        """Build Section 3: Question analysis."""
        story = []
        
        story.append(Paragraph("SECTION 3 — ANALYSE QUESTION PAR QUESTION", self.styles['SectionHeader']))

        # Questions table
        table_data = [['Q', 'Domaine', 'Compétence', 'Moy/Max', 'Réussite%', 'Blancs%']]
        
        for q in questions_data[:20]:  # Limit to first 20 questions
            q_info = q['question']
            table_data.append([
                str(q_info['number']),
                q_info.get('domain', 'N/A'),
                q_info.get('competence', 'N/A'),
                f"{q['mean_score']}/{q_info['max_points']}",
                f"{q['success_rate']}%",
                f"{q['blank_rate']}%"
            ])

        questions_table = Table(table_data, colWidths=[0.5*inch, 1.5*inch, 1.5*inch, 1*inch, 1*inch, 1*inch])
        questions_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), '#d0d0d0'),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 1, black),
        ]))

        story.append(questions_table)

        return story

    def _build_section_competences(self, competences_data: Dict[str, Any]) -> list:
        """Build Section 4: Competence analysis."""
        story = []
        
        story.append(Paragraph("SECTION 4 — MAÎTRISE DES COMPÉTENCES DNB", self.styles['SectionHeader']))

        # Competence table
        comp_stats = competences_data['data']
        table_data = [['Compétence', 'Maîtrise%', 'Niveau']]
        
        competence_levels = {
            'chercher': 'Chercher',
            'modéliser': 'Modéliser',
            'représenter': 'Représenter',
            'raisonner': 'Raisonner',
            'calculer': 'Calculer',
            'communiquer': 'Communiquer'
        }
        
        for comp_key, level in competence_levels.items():
            rate = comp_stats.get(comp_key, 0)
            if rate >= 70:
                niveau = "Maîtrisé"
            elif rate >= 50:
                niveau = "En cours"
            else:
                niveau = "À renforcer"
            table_data.append([level, f"{rate}%", niveau])

        comp_table = Table(table_data, colWidths=[2*inch, 1.5*inch, 1.5*inch])
        comp_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), '#d0d0d0'),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('GRID', (0, 0), (-1, -1), 1, black),
        ]))

        story.append(comp_table)
        story.append(Spacer(1, 20))

        # LLM analysis
        analysis = competences_data.get('analysis', '')
        if analysis:
            story.append(Paragraph("Analyse des compétences:", self.styles['Subsection']))
            story.append(Paragraph(analysis, self.styles['BodyText']))

        return story

    def _build_section_correctors(self, correctors_data: Dict[str, Any]) -> list:
        """Build Section 5: Inter-corrector analysis."""
        story = []
        
        story.append(Paragraph("SECTION 5 — ANALYSE INTER-CORRECTEURS", self.styles['SectionHeader']))

        # Correctors table
        corr_stats = correctors_data['data']
        table_data = [['Correcteur', 'Copies', 'Moyenne', 'Δ vs moy', 'σ', 'Profil']]
        
        for c in corr_stats:
            table_data.append([
                c['corrector__name'],
                str(c['n']),
                f"{c['mean']}/20",
                f"{c['delta_from_mean']:+.2f}",
                f"{c['std']:.2f}",
                c['severity']
            ])

        corr_table = Table(table_data, colWidths=[2*inch, 0.8*inch, 1*inch, 1*inch, 0.8*inch, 1.2*inch])
        corr_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), '#d0d0d0'),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 1, black),
        ]))

        story.append(corr_table)
        story.append(Spacer(1, 20))

        # LLM analysis
        analysis = correctors_data.get('analysis', '')
        if analysis:
            story.append(Paragraph("Analyse de la cohérence:", self.styles['Subsection']))
            story.append(Paragraph(analysis, self.styles['BodyText']))

        return story

    def _build_section_profiles(self, profiles_data: Dict[str, Any]) -> list:
        """Build Section 6: Student profiles."""
        story = []
        
        story.append(Paragraph("SECTION 6 — PROFILS DE LA PROMOTION", self.styles['SectionHeader']))

        # At-risk students
        at_risk = profiles_data.get('at_risk', [])
        if at_risk:
            story.append(Paragraph(f"Élèves à risque ({len(at_risk)}):", self.styles['Subsection']))
            
            risk_table_data = [['Élève', 'Classe', 'P1', 'P2']]
            for student in at_risk[:10]:  # Limit to 10
                risk_table_data.append([
                    student['name'],
                    student['class'],
                    str(student['p1']),
                    str(student['p2'])
                ])

            risk_table = Table(risk_table_data, colWidths=[2*inch, 1*inch, 0.8*inch, 0.8*inch])
            risk_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), '#d0d0d0'),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 8),
                ('GRID', (0, 0), (-1, -1), 1, black),
            ]))

            story.append(risk_table)

        return story

    def _build_section_recommendations(self, recommendations: str) -> list:
        """Build Section 7: Recommendations."""
        story = []
        
        story.append(Paragraph("SECTION 7 — RECOMMANDATIONS PÉDAGOGIQUES", self.styles['SectionHeader']))
        
        if recommendations:
            story.append(Paragraph(recommendations, self.styles['BodyText']))

        return story
