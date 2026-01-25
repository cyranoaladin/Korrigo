import { execSync } from 'node:child_process';

export default async () => {
    // Seed via docker (prod-like)
    console.log("Seeding E2E Data...");
    try {
        const pwd = process.cwd();
        // Assuming running from frontend/
        // Mount backend/scripts to /app/scripts
        const scriptPath = `${pwd}/../backend/scripts`;
        execSync(
            `docker compose -f ../infra/docker/docker-compose.local-prod.yml run --rm -v ${scriptPath}:/app/scripts -e PYTHONPATH=/app --entrypoint "python scripts/seed_e2e.py" backend`,
            { stdio: 'inherit' }
        );
    } catch (e) {
        console.error("Failed to seed data", e);
        throw e;
    }
};
