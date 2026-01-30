import { execSync } from 'node:child_process';

export default async () => {
    // Seed via docker (prod-like)
    console.log("Seeding E2E Data...");
    try {
        execSync(
            'docker compose -f ../infra/docker/docker-compose.local-prod.yml exec backend sh -c "export PYTHONPATH=/app && python scripts/seed_e2e.py"',
            { stdio: 'inherit' }
        );
    } catch (e) {
        console.error("Failed to seed data", e);
        throw e;
    }
};
