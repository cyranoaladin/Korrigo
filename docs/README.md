# Korrigo PMF Documentation

**Last Updated**: 30 Janvier 2026  
**Version**: 1.0.0

---

## 📚 Documentation Index

### For End Users

#### Administrators
- [Administration Guide](user/GUIDE_ADMINISTRATEUR.md) - *(To be created)*
- [FAQ](support/FAQ.md) - Comprehensive FAQ by user role
- [Support Procedures](support/SUPPORT.md) - Support levels and escalation

#### Teachers
- [Teacher Guide](user/GUIDE_ENSEIGNANT.md) - *(To be created)*
- [Walkthrough](user/walkthrough.md) - Interactive platform walkthrough

#### Secretariat
- [Secretariat Guide](user/GUIDE_SECRETARIAT.md) - *(To be created)*

#### Students  
- [Student Guide](user/GUIDE_ELEVE.md) - *(To be created)*

### For Support & Operations

- **[FAQ](support/FAQ.md)** - Frequently Asked Questions organized by role
- **[Troubleshooting Guide](support/DEPANNAGE.md)** - Diagnostic procedures and common issues
- **[Support Procedures](support/SUPPORT.md)** - Support levels, SLA, escalation matrix

### For Developers

- **[Development Guide](development/DEVELOPMENT_GUIDE.md)** - Local development environment setup
- **[Specification](development/SPECIFICATION.md)** - Project specification and requirements
- **[API Reference](technical/API_REFERENCE.md)** - REST API endpoints documentation
- **[Testing Guide](quality/TEST_PLAN.md)** - Test strategy and execution

### For System Architects

- **[Architecture](technical/ARCHITECTURE.md)** - System architecture and design
- **[Business Workflows](technical/BUSINESS_WORKFLOWS.md)** - Business process flows
- **[Database Schema](technical/DATABASE_SCHEMA.md)** - Database models and relationships
- **[PDF Processing](technical/PDF_PROCESSING.md)** - PDF validation and processing pipeline
- **[Technical Manual](technical/TECHNICAL_MANUAL.md)** - Technical reference

### For DevOps & Deployment

- **[Deployment Guide](deployment/DEPLOYMENT_GUIDE.md)** - Complete deployment instructions
- **[Production Runbook](deployment/RUNBOOK_PRODUCTION.md)** - Production operations
- **[Staging Runbook](deployment/RUNBOOK_STAGING.md)** - Staging environment operations
- **[Docker Production](deployment/DEPLOY_PRODUCTION.md)** - Docker deployment specifics

### For Quality Assurance

- **[Test Plan](quality/TEST_PLAN.md)** - Test plan and test coverage
- **[CI/CD Workflows](quality/CI_WORKFLOWS.md)** - Continuous integration setup
- **[Local Production Testing](quality/RUNBOOK_LOCAL_PRODLIKE.md)** - Local prod-like environment

### Architecture Decision Records (ADRs)

- **[ADR Index](decisions/README.md)** - List of all architecture decisions
- [ADR-001: Student Authentication Model](decisions/ADR-001-student-authentication-model.md)
- [ADR-002: PDF Coordinate Normalization](decisions/ADR-002-pdf-coordinate-normalization.md)
- [ADR-003: Copy Status State Machine](decisions/ADR-003-copy-status-state-machine.md)

---

## 📂 Documentation Structure

```
docs/
├── README.md                    # This file - Documentation index
├── user/                        # End-user guides by role
├── support/                     # Support and troubleshooting
├── technical/                   # Technical architecture docs
├── development/                 # Developer guides
├── deployment/                  # Deployment and operations
├── quality/                     # QA and testing docs
├── decisions/                   # Architecture Decision Records (ADRs)
└── archive/                     # Historical documents
```

---

## 🚀 Quick Start

**New to Korrigo?**
1. Read the [Walkthrough](user/walkthrough.md) for an overview
2. Check the [FAQ](support/FAQ.md) for common questions
3. See your role-specific guide (Admin/Teacher/Secretariat/Student)

**Setting up development?**
1. Follow the [Development Guide](development/DEVELOPMENT_GUIDE.md)
2. Review the [Architecture](technical/ARCHITECTURE.md)
3. Check the [API Reference](technical/API_REFERENCE.md)

**Deploying to production?**
1. Read the [Deployment Guide](deployment/DEPLOYMENT_GUIDE.md)
2. Follow the [Production Runbook](deployment/RUNBOOK_PRODUCTION.md)
3. Review security best practices in technical docs

**Troubleshooting issues?**
1. Check the [FAQ](support/FAQ.md) first
2. Use the [Troubleshooting Guide](support/DEPANNAGE.md)
3. Follow [Support Procedures](support/SUPPORT.md) for escalation

---

## 📞 Support

- **L1 Support**: School administrator (see [Support Procedures](support/SUPPORT.md))
- **L2 Support**: Technical IT team
- **L3 Support**: Korrigo vendor

For support procedures and SLA, see [Support Documentation](support/SUPPORT.md).

---

## 📜 License & Legal

- [Changelog](../CHANGELOG.md)
- [Release Notes](../RELEASE_NOTES_v1.0.0.md)

---

**Maintained by**: Korrigo PMF Team  
**Last Review**: 30 Janvier 2026
