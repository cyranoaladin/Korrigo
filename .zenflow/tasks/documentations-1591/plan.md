# Spec and build

## Configuration
- **Artifacts Path**: {@artifacts_path} → `.zenflow/tasks/{task_id}`

---

## Agent Instructions

Ask the user questions when anything is unclear or needs their input. This includes:
- Ambiguous or incomplete requirements
- Technical decisions that affect architecture or user experience
- Trade-offs that require business context

Do not make assumptions on important decisions — get clarification first.

---

## Workflow Steps

### [x] Step: Technical Specification
<!-- chat-id: 0438406f-8269-4d6e-8857-88cba8d5b750 -->

Assess the task's difficulty, as underestimating it leads to poor outcomes.
- easy: Straightforward implementation, trivial bug fix or feature
- medium: Moderate complexity, some edge cases or caveats to consider
- hard: Complex logic, many caveats, architectural considerations, or high-risk changes

Create a technical specification for the task that is appropriate for the complexity level:
- Review the existing codebase architecture and identify reusable components.
- Define the implementation approach based on established patterns in the project.
- Identify all source code files that will be created or modified.
- Define any necessary data model, API, or interface changes.
- Describe verification steps using the project's test and lint commands.

Save the output to `{@artifacts_path}/spec.md` with:
- Technical context (language, dependencies)
- Implementation approach
- Source code structure changes
- Data model / API / interface changes
- Verification approach

If the task is complex enough, create a detailed implementation plan based on `{@artifacts_path}/spec.md`:
- Break down the work into concrete tasks (incrementable, testable milestones)
- Each task should reference relevant contracts and include verification steps
- Replace the Implementation step below with the planned tasks

Rule of thumb for step size: each step should represent a coherent unit of work (e.g., implement a component, add an API endpoint, write tests for a module). Avoid steps that are too granular (single function).

Save to `{@artifacts_path}/plan.md`. If the feature is trivial and doesn't warrant this breakdown, keep the Implementation step below as is.

---

### [ ] Step: Phase 1 - School Administrator Documentation
<!-- chat-id: fe22a2b2-442b-47f6-995c-a78c8bb26f57 -->

Create comprehensive documentation for school administrators and leadership.

**Files to create:**
1. `docs/admin/GUIDE_ADMINISTRATEUR_LYCEE.md` (~25-30 KB)
   - Non-technical executive guide for school leadership
   - System overview, deployment, legal compliance, governance
   
2. `docs/admin/GUIDE_UTILISATEUR_ADMIN.md` (~30-35 KB)
   - Technical admin user manual
   - User management, exam management, system config, monitoring
   
3. `docs/admin/GESTION_UTILISATEURS.md` (~15-18 KB)
   - User management procedures
   - Creating/deactivating users, role assignment, bulk import
   
4. `docs/admin/PROCEDURES_OPERATIONNELLES.md` (~25-30 KB)
   - Daily operations, exam lifecycle, maintenance, change management

**Verification:**
- [ ] All files use French language
- [ ] Non-technical language for GUIDE_ADMINISTRATEUR_LYCEE.md
- [ ] Cross-references to security and RGPD docs are valid
- [ ] Each document has proper front matter (version, date, audience)
- [ ] Table of contents matches sections

---

### [ ] Step: Phase 2 - User Role Documentation
<!-- chat-id: e18dbbae-1cd9-469a-8208-6801b97a1db4 -->

Create role-specific user guides for all platform users.

**Files to create:**
1. `docs/users/GUIDE_ENSEIGNANT.md` (~20-25 KB)
   - Teacher user manual
   - Login, grading workflow, annotations, best practices
   
2. `docs/users/GUIDE_SECRETARIAT.md` (~15-20 KB)
   - Secretariat/identification desk guide
   - Copy identification, OCR, booklet management, student database
   
3. `docs/users/GUIDE_ETUDIANT.md` (~10-12 KB)
   - Student portal guide (simple French)
   - Login, viewing copies, understanding grades, privacy
   
4. `docs/users/NAVIGATION_UI.md` (~25-30 KB)
   - Complete UI navigation reference with screenshots
   - All views, components, navigation flows by role

**Verification:**
- [ ] Simple, non-technical language
- [ ] Step-by-step instructions with examples
- [ ] Screenshots/diagrams for NAVIGATION_UI.md
- [ ] Each role guide addresses specific workflows
- [ ] Cross-references to FAQ and troubleshooting

---

### [ ] Step: Phase 3 - Security & Compliance Documentation
<!-- chat-id: fef72ba2-92f5-46fa-8b15-49dc425c2ff4 -->

Create comprehensive security and RGPD compliance documentation.

**Files to create:**
1. `docs/security/POLITIQUE_RGPD.md` (~30-35 KB)
   - Complete RGPD/GDPR compliance policy
   - Legal framework, data inventory, subject rights, retention, security measures
   - CNIL compliance requirements
   
2. `docs/security/MANUEL_SECURITE.md` (~25-30 KB)
   - Technical security manual
   - Authentication, access control, data security, audit logging, incident response
   
3. `docs/security/GESTION_DONNEES.md` (~20-25 KB)
   - Data management guide
   - Data lifecycle, storage, backup, retention, export, deletion
   
4. `docs/security/AUDIT_CONFORMITE.md` (~12-15 KB)
   - Compliance audit procedures
   - Audit methodology, schedule, reporting, corrective actions

**Verification:**
- [ ] RGPD policy aligned with French law and CNIL guidelines
- [ ] Security manual references actual implementation (SECURITY_PERMISSIONS_INVENTORY.md)
- [ ] Data retention policies are legally compliant
- [ ] Cross-references between security docs are accurate
- [ ] Technical accuracy verified against codebase

---

### [x] Step: Phase 4 - Legal Documentation
<!-- chat-id: 3c1ff13f-e390-43fa-97e1-01a08888fbda -->

Create legal and compliance documents for users and school.

**Files to create:**
1. `docs/legal/POLITIQUE_CONFIDENTIALITE.md` (~10-12 KB)
   - User-facing privacy policy (simple French)
   - What data is collected, why, rights, contact
   
2. `docs/legal/CONDITIONS_UTILISATION.md` (~8-10 KB)
   - Terms of service
   - Acceptable use, liabilities, disclaimers
   
3. `docs/legal/ACCORD_TRAITEMENT_DONNEES.md` (~12-15 KB)
   - Data processing agreement (DPA)
   - School as controller, Korrigo as processor
   
4. `docs/legal/FORMULAIRES_CONSENTEMENT.md` (~5-8 KB)
   - Consent form templates
   - Parent consent, student consent (if required)

**Verification:**
- [ ] Simple language for POLITIQUE_CONFIDENTIALITE.md
- [ ] Legal terminology appropriate for French educational context
- [ ] DPA follows RGPD Article 28 requirements
- [ ] Consent forms include all required elements
- [ ] Cross-references to POLITIQUE_RGPD.md

---

### [ ] Step: Phase 5 - Support & Troubleshooting Documentation
<!-- chat-id: 51a38824-8475-47f9-9325-a20b3833950a -->

Create comprehensive support and troubleshooting resources.

**Files to create:**
1. `docs/support/FAQ.md` (~20-25 KB)
   - Comprehensive FAQ organized by role
   - General, Admin, Teacher, Secretary, Student, Technical sections
   
2. `docs/support/DEPANNAGE.md` (~15-20 KB)
   - Troubleshooting guide
   - Diagnostic procedures, common issues by category, emergency procedures
   
3. `docs/support/SUPPORT.md` (~8-10 KB)
   - Support procedures and contact information
   - Escalation matrix, SLA (if applicable), documentation maintenance

**Verification:**
- [ ] FAQ answers are clear and actionable
- [ ] Troubleshooting guide includes diagnostic commands
- [ ] Common issues from existing docs are included
- [ ] Support procedures are realistic for school environment
- [ ] Cross-references to user guides and technical docs

---

### [ ] Step: Documentation Integration & Index
<!-- chat-id: da0a3750-1862-4ebf-bac6-53b26da9f698 -->

Create master documentation index and validate all cross-references.

**Tasks:**
1. Create `docs/INDEX.md` - Master index linking all documentation
   - Organized by audience (Admin, Teacher, Student, Technical)
   - Brief description of each document
   - Quick start guide pointing to right docs
   
2. Update root `README.md` - Add documentation section
   - Link to docs/INDEX.md
   - Brief overview of available documentation
   
3. Create `docs/admin/README.md`, `docs/users/README.md`, `docs/security/README.md`, `docs/legal/README.md`, `docs/support/README.md`
   - Section-specific indexes
   
4. Validate all cross-references
   - Run script to check all internal links
   - Verify all referenced sections exist
   - Fix broken links

**Verification:**
- [ ] INDEX.md provides clear navigation for all audiences
- [ ] All cross-references resolve correctly
- [ ] No broken internal links
- [ ] Consistent terminology across all documents
- [ ] Version numbers are consistent

---

### [ ] Step: Quality Review & Final Validation

Perform comprehensive quality review of all documentation.

**Review Checklist:**

**Completeness:**
- [ ] All 17 documentation files created
- [ ] All required sections present in each document
- [ ] Total content: 180-250 KB
- [ ] All user roles covered (Admin, Teacher, Secretary, Student)
- [ ] All aspects covered (technical, usage, security, RGPD, legal, operational)

**Accuracy:**
- [ ] Technical details match actual implementation
- [ ] API endpoints verified against docs/API_REFERENCE.md
- [ ] Workflows match docs/BUSINESS_WORKFLOWS.md
- [ ] Security controls match SECURITY_PERMISSIONS_INVENTORY.md
- [ ] Database references match docs/DATABASE_SCHEMA.md

**Language & Clarity:**
- [ ] All documents in French
- [ ] Non-technical docs use simple language
- [ ] Technical docs are precise and accurate
- [ ] Examples are relevant and helpful
- [ ] Glossaries provided where needed

**Legal & Compliance:**
- [ ] RGPD policy covers all CNIL requirements
- [ ] Data retention policies are legally sound
- [ ] Privacy policy is user-friendly
- [ ] DPA follows Article 28 requirements
- [ ] Consent forms include all required elements

**Cross-References:**
- [ ] All links resolve correctly
- [ ] Bidirectional references are complete
- [ ] No contradictions between documents
- [ ] Consistent terminology

**Final Tasks:**
- [ ] Spell check all French content
- [ ] Format consistency (headers, lists, tables)
- [ ] Generate final report in `{@artifacts_path}/report.md`

**Report Contents:**
- List of all documentation created
- Total size and word count
- Key features and highlights
- Challenges encountered
- Recommendations for maintenance
- Next steps (screenshots, translations if needed)
