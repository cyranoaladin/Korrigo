"""
GET /api/exams/stats-report/
Computes ALL jury report statistics dynamically from the database.
Admin-only endpoint consumed by StatsReport.vue.
"""
import statistics
from collections import defaultdict

from django.db.models import Count, Q
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from exams.models import Exam, Copy
from exams.permissions import IsTeacherOrAdmin
from grading.models import Score, Annotation, QuestionRemark
from grading.services import GradingService
from students.models import Student


class StatsReportView(APIView):
    """Full jury report data — no hardcoded values."""

    permission_classes = [IsAuthenticated, IsTeacherOrAdmin]  # LOT 8 FIX: was IsAuthenticated only

    # ------------------------------------------------------------------ helpers
    @staticmethod
    def _scores_for_copies(copies_qs):
        """Return list of (copy, total_score) for GRADED copies."""
        results = []
        for c in copies_qs.select_related('student', 'assigned_corrector'):
            score_obj = Score.objects.filter(copy=c).first()
            if score_obj and score_obj.scores_data:
                total = round(sum(
                    float(v) for v in score_obj.scores_data.values()
                    if v is not None and str(v).strip() != ''
                ), 2)
                results.append((c, total))
        return results

    @staticmethod
    def _stat_block(scores):
        """Compute mean/median/std/min/max/q1/q3 for a list of floats."""
        if not scores:
            return {'n': 0, 'mean': None, 'median': None, 'std': None,
                    'min': None, 'max': None, 'q1': None, 'q3': None}
        s = sorted(scores)
        n = len(s)
        return {
            'n': n,
            'mean': round(statistics.mean(s), 2),
            'median': round(statistics.median(s), 2),
            'std': round(statistics.stdev(s), 2) if n > 1 else 0,
            'min': round(min(s), 2),
            'max': round(max(s), 2),
            'q1': round(s[n // 4], 2) if n >= 4 else round(s[0], 2),
            'q3': round(s[3 * n // 4], 2) if n >= 4 else round(s[-1], 2),
        }

    @staticmethod
    def _pass_info(scores):
        """Count >=10 and <10."""
        ge10 = sum(1 for s in scores if s >= 10)
        lt10 = len(scores) - ge10
        n = len(scores)
        rate = round(ge10 / n * 100, 1) if n else 0
        return {'ge10': ge10, 'lt10': lt10, 'rate': rate}

    @staticmethod
    def _distribution(scores, bins=None):
        """2-point bins for global distribution."""
        if bins is None:
            bins = [(0, 2), (2, 4), (4, 6), (6, 8), (8, 10),
                    (10, 12), (12, 14), (14, 16), (16, 18), (18, 20.01)]
        n = len(scores)
        result = []
        for lo, hi in bins:
            count = sum(1 for s in scores if lo <= s < hi)
            label = f'[{int(lo)};{int(hi) if hi <= 20 else 20}]' if hi > 20 else f'[{int(lo)};{int(hi)}['
            pct = round(count / n * 100, 1) if n else 0
            result.append({'label': label, 'count': count, 'pct': f'{pct}%'})
        return result

    @staticmethod
    def _mentions(j1_scores, j2_scores, all_scores):
        """Compute mentions breakdown."""
        def _count(scores, lo, hi=None):
            if hi is None:
                return sum(1 for s in scores if s >= lo)
            return sum(1 for s in scores if lo <= s < hi)

        n = len(all_scores)
        rows = [
            ('Très Bien', '≥ 16', 16, None),
            ('Bien', '[14;16[', 14, 16),
            ('Assez Bien', '[12;14[', 12, 14),
            ('Passable', '[10;12[', 10, 12),
            ('Insuffisant', '< 10', 0, 10),
        ]
        colors = [
            ('text-green-800', 'bg-green-500'),
            ('text-blue-800', 'bg-blue-500'),
            ('text-cyan-800', 'bg-cyan-500'),
            ('text-amber-800', 'bg-amber-500'),
            ('text-red-800', 'bg-red-500'),
        ]
        result = []
        for (label, seuil, lo, hi), (lc, dc) in zip(rows, colors):
            j1 = _count(j1_scores, lo, hi) if hi else _count(j1_scores, lo)
            j2 = _count(j2_scores, lo, hi) if hi else _count(j2_scores, lo)
            g = j1 + j2
            if label == 'Insuffisant':
                j1 = sum(1 for s in j1_scores if s < 10)
                j2 = sum(1 for s in j2_scores if s < 10)
                g = j1 + j2
            pct = round(g / n * 100, 1) if n else 0
            result.append({
                'label': label, 'seuil': seuil,
                'j1': j1, 'j2': j2, 'global': g,
                'pct': f'{pct}%',
                'labelColor': lc, 'dotColor': dc,
            })
        return result

    # ------------------------------------------------------------------ main
    def get(self, request):
        exams = {e.name: e for e in Exam.objects.all()}
        bb_j1 = exams.get('BB_J1')
        bb_j2 = exams.get('BB_J2')

        if not bb_j1 or not bb_j2:
            return Response({'error': 'BB_J1 or BB_J2 exam not found'}, status=404)

        # Gather scores
        j1_pairs = self._scores_for_copies(
            Copy.objects.filter(exam=bb_j1, status='FINALIZED'))
        j2_pairs = self._scores_for_copies(
            Copy.objects.filter(exam=bb_j2, status='FINALIZED'))

        j1_scores = sorted([t for _, t in j1_pairs])
        j2_scores = sorted([t for _, t in j2_pairs])
        all_scores = sorted(j1_scores + j2_scores)

        n_correctors = (
            Copy.objects.filter(status='FINALIZED')
            .values('assigned_corrector').distinct().count()
        )

        # ======================== HEADER ========================
        header = {
            'n_candidates': len(all_scores),
            'n_j1': len(j1_scores),
            'n_j2': len(j2_scores),
            'n_correctors': n_correctors,
        }

        # ======================== KPIs ========================
        g_pass = self._pass_info(all_scores)
        tb_count = sum(1 for s in all_scores if s >= 16)
        n = len(all_scores)
        kpis = {
            'global_mean': round(statistics.mean(all_scores), 2) if all_scores else 0,
            'pass_rate': g_pass['rate'],
            'pass_count': g_pass['ge10'],
            'total': n,
            'tb_rate': round(tb_count / n * 100, 1) if n else 0,
            'tb_count': tb_count,
            'difficulty_rate': round(g_pass['lt10'] / n * 100, 1) if n else 0,
            'difficulty_count': g_pass['lt10'],
        }

        # ======================== DESCRIPTIVE STATS ========================
        j1_stats = self._stat_block(j1_scores)
        j2_stats = self._stat_block(j2_scores)
        g_stats = self._stat_block(all_scores)
        j1_pass = self._pass_info(j1_scores)
        j2_pass = self._pass_info(j2_scores)

        descriptive_stats = {
            'j1': {**j1_stats, **j1_pass},
            'j2': {**j2_stats, **j2_pass},
            'global': {**g_stats, **g_pass},
        }

        # ======================== DISTRIBUTION ========================
        global_distribution = self._distribution(all_scores)

        # ======================== MENTIONS ========================
        mentions = self._mentions(j1_scores, j2_scores, all_scores)

        # ======================== CORRECTORS ========================
        correctors = self._compute_correctors(bb_j1, bb_j2, j1_pairs, j2_pairs)

        # ======================== GROUPS ========================
        has_groups = Student.objects.filter(
            copies__exam__in=[bb_j1, bb_j2]
        ).exclude(groupe__isnull=True).exclude(groupe='').exists()
        groups_j1 = self._compute_groups(j1_pairs, bb_j1)
        groups_j2 = self._compute_groups(j2_pairs, bb_j2)

        # ======================== CLASSES ========================
        classes_j1 = self._compute_classes(j1_pairs)
        classes_j2 = self._compute_classes(j2_pairs)

        # ======================== SUBJECTS A/B ========================
        subjects = self._compute_subjects(j1_pairs, j2_pairs)

        # ======================== QUESTIONS (BB_J2) ========================
        questions = self._compute_questions(bb_j2)

        # ======================== PALMARÈS ========================
        top15, bottom11 = self._compute_palmares(j1_pairs + j2_pairs)

        # ======================== QUALITY ========================
        quality = self._compute_quality()

        # ======================== QCM ========================
        qcm = self._compute_qcm(j1_pairs, j2_pairs, bb_j1, bb_j2)

        return Response({
            'header': header,
            'kpis': kpis,
            'descriptive_stats': descriptive_stats,
            'global_distribution': global_distribution,
            'mentions': mentions,
            'correctors': correctors,
            'has_groups': has_groups,
            'groups_j1': groups_j1,
            'groups_j2': groups_j2,
            'classes_j1': classes_j1,
            'classes_j2': classes_j2,
            'subjects': subjects,
            'questions': questions,
            'top15': top15,
            'bottom11': bottom11,
            'quality': quality,
            'qcm': qcm,
        })

    # ------------------------------------------------------------------ correctors
    def _compute_correctors(self, bb_j1, bb_j2, j1_pairs, j2_pairs):
        """Per-corrector stats."""
        corr_map = defaultdict(lambda: {'scores': [], 'exam': '', 'n_total': 0, 'n_finalized': 0})

        for exam, pairs, exam_name in [(bb_j1, j1_pairs, 'BB_J1'), (bb_j2, j2_pairs, 'BB_J2')]:
            corrector_totals = (
                Copy.objects.filter(exam=exam)
                .values('assigned_corrector__username',
                        'assigned_corrector__first_name',
                        'assigned_corrector__last_name')
                .annotate(total=Count('id'))
            )
            for ct in corrector_totals:
                uname = ct['assigned_corrector__username']
                if uname:
                    corr_map[uname]['n_total'] = ct['total']
                    corr_map[uname]['exam'] = exam_name
                    fn = ct['assigned_corrector__first_name'] or ''
                    ln = ct['assigned_corrector__last_name'] or ''
                    corr_map[uname]['name'] = f'{fn} {ln}'.strip() or uname.split('@')[0]

            for copy, score in pairs:
                if copy.assigned_corrector:
                    uname = copy.assigned_corrector.username
                    corr_map[uname]['scores'].append(score)
                    corr_map[uname]['exam'] = exam_name

        result = []
        for uname, data in corr_map.items():
            scores = data['scores']
            if not scores:
                continue
            st = self._stat_block(scores)
            pi = self._pass_info(scores)
            initials = ''.join(w[0].upper() for w in data.get('name', '').split() if w)[:2]
            result.append({
                'name': data.get('name', uname),
                'initials': initials,
                'exam': data['exam'],
                'n': data['n_total'],
                'finalized': len(scores),
                'mean': st['mean'],
                'median': str(st['median']),
                'std': str(st['std']),
                'min': str(st['min']),
                'max': str(st['max']),
                'rate': f"{pi['rate']}%",
            })
        result.sort(key=lambda x: -(x['mean'] or 0))
        return result

    # ------------------------------------------------------------------ groups
    def _compute_groups(self, pairs, exam):
        """Per-group stats. Teacher = most frequent corrector for that group."""
        group_data = defaultdict(lambda: {'scores': [], 'correctors': defaultdict(int)})

        for copy, score in pairs:
            if not copy.student:
                continue
            groupe = copy.student.groupe or 'Non assigné'
            group_data[groupe]['scores'].append(score)
            if copy.assigned_corrector:
                fn = copy.assigned_corrector.first_name or ''
                ln = copy.assigned_corrector.last_name or ''
                cname = f'{fn} {ln}'.strip() or copy.assigned_corrector.username.split('@')[0]
                group_data[groupe]['correctors'][cname] += 1

        result = []
        for groupe in sorted(group_data.keys(),
                             key=lambda g: -statistics.mean(group_data[g]['scores'])):
            scores = group_data[groupe]['scores']
            st = self._stat_block(scores)
            pi = self._pass_info(scores)
            teacher = max(group_data[groupe]['correctors'],
                          key=group_data[groupe]['correctors'].get,
                          default='—')
            result.append({
                'name': groupe,
                'teacher': teacher,
                'n': len(scores),
                'mean': str(st['mean']),
                'rate': f"{pi['rate']}%",
            })
        return result

    # ------------------------------------------------------------------ classes
    def _compute_classes(self, pairs):
        """Per-class stats."""
        class_data = defaultdict(list)
        for copy, score in pairs:
            if not copy.student:
                continue
            cn = copy.student.class_name or 'Inconnu'
            class_data[cn].append(score)

        result = []
        for cn in sorted(class_data.keys(),
                         key=lambda c: -statistics.mean(class_data[c])):
            scores = class_data[cn]
            st = self._stat_block(scores)
            pi = self._pass_info(scores)
            result.append({
                'name': cn,
                'n': len(scores),
                'mean': str(st['mean']),
                'std': str(st['std']),
                'rate': f"{pi['rate']}%",
                'rateNum': pi['rate'],
            })
        return result

    # ------------------------------------------------------------------ subjects A/B
    def _compute_subjects(self, j1_pairs, j2_pairs):
        """Subject A vs B comparison per exam."""
        result = {}
        for exam_label, pairs in [('j1', j1_pairs), ('j2', j2_pairs)]:
            a_scores = [t for c, t in pairs if c.subject_variant == 'A']
            b_scores = [t for c, t in pairs if c.subject_variant == 'B']
            result[f'{exam_label}_a'] = self._stat_block(a_scores)
            result[f'{exam_label}_b'] = self._stat_block(b_scores)
        return result

    # ------------------------------------------------------------------ questions
    def _compute_questions(self, exam):
        """Per-question stats for an exam (BB_J2)."""
        # Get q_max from grading_structure
        def _get_leaves(structure, parent=''):
            leaves = {}
            for i, item in enumerate(structure):
                qid = f'{parent}.{i+1}' if parent else f'{i+1}'
                children = item.get('children', [])
                if children:
                    leaves.update(_get_leaves(children, qid))
                else:
                    leaves[qid] = item.get('points', 0)
            return leaves

        q_max = _get_leaves(exam.grading_structure)

        all_sd = []
        for c in Copy.objects.filter(exam=exam, status='FINALIZED'):
            score_obj = Score.objects.filter(copy=c).first()
            if score_obj and score_obj.scores_data:
                all_sd.append(score_obj.scores_data)

        n = len(all_sd)
        if n == 0:
            return []

        result = []
        # Sort question IDs naturally
        def _sort_key(qid):
            return [int(p) if p.isdigit() else p for p in qid.split('.')]

        for qid in sorted(q_max.keys(), key=_sort_key):
            mx = float(q_max[qid])
            vals = [float(sd.get(qid, 0) or 0) for sd in all_sd]
            mean_q = round(statistics.mean(vals), 2)
            zeros_pct = round(sum(1 for v in vals if v == 0) / n * 100, 1)
            max_pct = round(sum(1 for v in vals if abs(v - mx) < 0.01) / n * 100, 1)

            # Auto-classify difficulty
            ratio = mean_q / mx if mx > 0 else 0
            if max_pct >= 60:
                difficulty = 'Facile'
            elif zeros_pct >= 30 or ratio < 0.4:
                difficulty = 'Difficile'
            else:
                difficulty = 'Moyen'

            # Build display ID (prefix Q + exercise number)
            parts = qid.split('.')
            display_id = f'Q{qid}' if len(parts) > 1 else f'Q{qid} (QCM)' if mx == 5.0 else f'Q{qid}'

            result.append({
                'id': display_id,
                'qid': qid,
                'max': mx,
                'mean': mean_q,
                'zeros': zeros_pct,
                'maxPct': max_pct,
                'difficulty': difficulty,
                'hard': difficulty == 'Difficile',
            })
        return result

    # ------------------------------------------------------------------ palmarès
    def _compute_palmares(self, all_pairs):
        """Top 15 and bottom students (<5/20)."""
        ranked = []
        for copy, score in all_pairs:
            if not copy.student:
                continue
            s = copy.student
            ln = s.last_name or ''
            fn = s.first_name or ''
            display_name = f'{ln} {fn.title()}'.strip() if ln else str(s)

            corr_name = ''
            if copy.assigned_corrector:
                cfn = copy.assigned_corrector.first_name or ''
                cln = copy.assigned_corrector.last_name or ''
                corr_name = f'{cfn} {cln}'.strip() or copy.assigned_corrector.username.split('@')[0]

            ranked.append({
                'name': display_name,
                'classe': s.class_name or '?',
                'groupe': s.groupe or '?',
                'exam': copy.exam.name,
                'note': f'{score:.2f}',
                'score_num': score,
                'corrector': corr_name,
            })

        ranked.sort(key=lambda x: -x['score_num'])

        # Top 15 with proper ranking (ties get same rank)
        top15 = []
        prev_score = None
        prev_rank = 0
        for i, entry in enumerate(ranked[:15]):
            if entry['score_num'] != prev_score:
                prev_rank = i + 1
                prev_score = entry['score_num']
            top15.append({**entry, 'rank': prev_rank})

        # Bottom: all students < 5/20
        bottom_all = [e for e in ranked if e['score_num'] < 5]
        bottom_all.sort(key=lambda x: x['score_num'])
        bottom = []
        for i, entry in enumerate(bottom_all):
            rank = len(ranked) - i
            bottom.append({**entry, 'rank': rank})

        return top15, bottom

    # ------------------------------------------------------------------ quality
    def _compute_quality(self):
        """Quality KPIs: remarks, annotations, appreciations, LLM summaries."""
        total_copies = Copy.objects.filter(status='FINALIZED').count()

        remarks_count = QuestionRemark.objects.count()
        copies_with_remarks = (
            QuestionRemark.objects.values('copy').distinct().count()
        )

        annotations_count = Annotation.objects.count()
        copies_with_annotations = (
            Annotation.objects.values('copy').distinct().count()
        )

        copies_with_appreciation = (
            Copy.objects.filter(status='FINALIZED')
            .exclude(Q(global_appreciation__isnull=True) | Q(global_appreciation=''))
            .count()
        )
        appreciation_rate = round(copies_with_appreciation / total_copies * 100) if total_copies else 0

        copies_with_llm = (
            Copy.objects.filter(status='FINALIZED')
            .exclude(Q(llm_summary__isnull=True) | Q(llm_summary=''))
            .count()
        )
        llm_pct = round(copies_with_llm / total_copies * 100, 1) if total_copies else 0

        # Appreciation tags frequency
        appreciation_tags = self._compute_appreciation_tags()

        return {
            'remarks_count': remarks_count,
            'copies_with_remarks': copies_with_remarks,
            'annotations_count': annotations_count,
            'copies_with_annotations': copies_with_annotations,
            'appreciation_rate': f'{appreciation_rate}%',
            'copies_with_appreciation': copies_with_appreciation,
            'llm_count': copies_with_llm,
            'llm_pct': llm_pct,
            'total_copies': total_copies,
            'appreciation_tags': appreciation_tags,
        }

    def _compute_appreciation_tags(self):
        """Count frequency of common appreciation keywords."""
        tags_keywords = [
            ('Très Bien', ['très bien', 'tres bien']),
            ('Bien', ['bien']),
            ('Excellent', ['excellent']),
            ('Ensemble Moyen', ['ensemble moyen']),
            ('Assez Bien', ['assez bien']),
            ('Ensemble Juste', ['ensemble juste']),
            ('Insuffisant', ['insuffisant']),
            ('Bien juste', ['bien juste']),
            ('Ensemble Correct', ['ensemble correct']),
        ]
        appreciations = list(
            Copy.objects.filter(status='FINALIZED')
            .exclude(Q(global_appreciation__isnull=True) | Q(global_appreciation=''))
            .values_list('global_appreciation', flat=True)
        )

        tag_colors = [
            'bg-green-50 border-green-200 text-green-800',
            'bg-blue-50 border-blue-200 text-blue-800',
            'bg-amber-50 border-amber-200 text-amber-800',
            'bg-gray-50 border-gray-200 text-gray-700',
            'bg-cyan-50 border-cyan-200 text-cyan-800',
            'bg-yellow-50 border-yellow-200 text-yellow-800',
            'bg-red-50 border-red-200 text-red-800',
            'bg-orange-50 border-orange-200 text-orange-800',
            'bg-teal-50 border-teal-200 text-teal-800',
        ]

        result = []
        matched_indices = set()

        for (tag, keywords), css_class in zip(tags_keywords, tag_colors):
            count = 0
            for i, appr in enumerate(appreciations):
                if i in matched_indices:
                    continue
                lower = appr.lower().strip()
                for kw in keywords:
                    if kw in lower:
                        # Avoid "Très Bien" matching generic "Bien"
                        if tag == 'Bien' and ('très bien' in lower or 'assez bien' in lower or 'bien juste' in lower):
                            continue
                        count += 1
                        matched_indices.add(i)
                        break
            if count > 0:
                result.append({'text': tag, 'count': count, 'class': css_class})

        result.sort(key=lambda x: -x['count'])
        return result

    # ------------------------------------------------------------------ QCM
    def _compute_qcm(self, j1_pairs, j2_pairs, bb_j1, bb_j2):
        """QCM analysis: Ex1 distribution, 5/5 students, etc."""
        def _get_ex1_score(copy):
            """Get Exercise 1 (QCM) score — question ID '1' in scores_data."""
            score_obj = Score.objects.filter(copy=copy).first()
            if not score_obj or not score_obj.scores_data:
                return None
            # For BB_J1, Ex1 might be split into sub-questions or a single '1'
            # For BB_J2, it's question '1' (5pts)
            sd = score_obj.scores_data
            if '1' in sd:
                v = sd['1']
                return float(v) if v is not None and str(v).strip() != '' else None
            # Sum all 1.x keys
            ex1_total = 0
            found = False
            for k, v in sd.items():
                if k.startswith('1.') or k == '1':
                    if v is not None and str(v).strip() != '':
                        ex1_total += float(v)
                        found = True
            return ex1_total if found else None

        def _build_dist(scores, step=1.0):
            """Build distribution of Ex1 scores."""
            if not scores:
                return []
            mx = max(scores)
            n = len(scores)
            bins = []
            val = 0
            while val <= mx + 0.01:
                count = sum(1 for s in scores if abs(s - val) < 0.01)
                if count > 0:
                    if val == int(val):
                        label = f'{int(val)}/5'
                    else:
                        label = str(val)
                    pct = round(count / n * 100, 1)
                    bins.append({'label': label, 'count': count, 'pct': f'{pct}%'})
                val = round(val + 0.5, 1)
            return bins

        # Get Ex1 scores for each exam
        j1_ex1 = []
        j2_ex1 = []
        for copy, total in j1_pairs:
            e1 = _get_ex1_score(copy)
            if e1 is not None:
                j1_ex1.append((copy, total, e1))
        for copy, total in j2_pairs:
            e1 = _get_ex1_score(copy)
            if e1 is not None:
                j2_ex1.append((copy, total, e1))

        j1_ex1_scores = [e for _, _, e in j1_ex1]
        j2_ex1_scores = [e for _, _, e in j2_ex1]

        # Perfect QCM (5/5)
        j1_perfect = [(c, t, e) for c, t, e in j1_ex1 if abs(e - 5.0) < 0.01]
        j2_perfect = [(c, t, e) for c, t, e in j2_ex1 if abs(e - 5.0) < 0.01]
        all_perfect = j1_perfect + j2_perfect
        all_perfect.sort(key=lambda x: -x[1])

        perfect_list = []
        for copy, total, ex1 in all_perfect:
            s = copy.student
            if not s:
                continue
            ln = s.last_name or ''
            fn = s.first_name or ''
            display_name = f'{ln} {fn.title()}'.strip() if ln else str(s)

            corr_name = ''
            if copy.assigned_corrector:
                cfn = copy.assigned_corrector.first_name or ''
                cln = copy.assigned_corrector.last_name or ''
                corr_name = f'{cfn} {cln}'.strip()

            pct = round(5.0 / total * 100, 1) if total > 0 else 0
            perfect_list.append({
                'name': display_name,
                'exam': copy.exam.name,
                'classe': s.class_name or '?',
                'groupe': s.groupe or '?',
                'total': total,
                'pct': pct,
                'corrector': corr_name,
            })

        # Students with 5/5 QCM but < 10/20 total
        below10_with_perfect = sum(1 for _, t, _ in all_perfect if t < 10)

        j1_mean_ex1 = round(statistics.mean(j1_ex1_scores), 2) if j1_ex1_scores else 0
        j2_mean_ex1 = round(statistics.mean(j2_ex1_scores), 2) if j2_ex1_scores else 0

        return {
            'dist_j1': _build_dist(j1_ex1_scores),
            'dist_j2': _build_dist(j2_ex1_scores),
            'perfect': perfect_list,
            'total_perfect': len(all_perfect),
            'j1_perfect_count': len(j1_perfect),
            'j2_perfect_count': len(j2_perfect),
            'j1_perfect_pct': round(len(j1_perfect) / len(j1_ex1) * 100, 1) if j1_ex1 else 0,
            'j2_perfect_pct': round(len(j2_perfect) / len(j2_ex1) * 100, 1) if j2_ex1 else 0,
            'total_perfect_pct': round(len(all_perfect) / (len(j1_ex1) + len(j2_ex1)) * 100, 1) if (j1_ex1 or j2_ex1) else 0,
            'below10_with_perfect': below10_with_perfect,
            'j1_mean_ex1': j1_mean_ex1,
            'j2_mean_ex1': j2_mean_ex1,
        }
