from pathlib import Path
import stat
import unittest


def repo_root_from(anchor: str | Path) -> Path:
    anchor_path = Path(anchor).resolve()
    for candidate in list(anchor_path.parents) + [Path.cwd().resolve()]:
        if (
            (candidate / "backend").is_dir()
            and (candidate / "infra").is_dir()
            and (candidate / "scripts").is_dir()
        ):
            return candidate
    raise FileNotFoundError("Could not resolve Korrigo repository root")


REPO_ROOT = repo_root_from(__file__)
INVENTORY_SCRIPT = REPO_ROOT / "scripts" / "ops" / "korrigo_docker_cleanup_inventory.sh"


class KorrigoCleanupInventoryContractTests(unittest.TestCase):
    def test_inventory_script_exists_and_is_executable(self):
        self.assertTrue(INVENTORY_SCRIPT.exists())
        mode = INVENTORY_SCRIPT.stat().st_mode
        self.assertTrue(mode & stat.S_IXUSR)

    def test_inventory_script_is_strict_dry_run(self):
        text = INVENTORY_SCRIPT.read_text()

        self.assertIn("set -euo pipefail", text)
        self.assertIn("DRY_RUN_ONLY=YES", text)
        self.assertIn("NO_DELETION_PERFORMED=YES", text)

    def test_inventory_script_does_not_contain_destructive_commands(self):
        text = INVENTORY_SCRIPT.read_text()
        forbidden = [
            "docker rmi",
            "docker image rm",
            "docker system prune",
            "docker volume prune",
            "docker network prune",
            "docker compose down",
            "down -v",
            "docker compose up",
            "rm -rf",
            "docker volume rm",
            "docker network rm",
            "docker container rm",
        ]

        for needle in forbidden:
            self.assertNotIn(needle, text, f"{needle!r} must not appear in {INVENTORY_SCRIPT}")

    def test_inventory_script_collects_read_only_docker_state(self):
        text = INVENTORY_SCRIPT.read_text()

        self.assertIn("docker ps", text)
        self.assertIn("docker images", text)
        self.assertIn("docker volume ls", text)
        self.assertIn("candidate_korrigo_images_dry_run.txt", text)
        self.assertIn("protected_images_observed.txt", text)


if __name__ == "__main__":
    unittest.main()
