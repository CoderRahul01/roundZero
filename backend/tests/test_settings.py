import unittest

from settings import LOCAL_DEV_ORIGINS, Settings


class SettingsCorsTests(unittest.TestCase):
    def test_normalized_cors_origins_adds_common_loopback_ports(self) -> None:
        settings = Settings(cors_allow_origins=["http://localhost:3000"])

        origins = settings.normalized_cors_origins()

        self.assertIn("http://localhost:3001", origins)
        self.assertIn("http://localhost:5173", origins)

    def test_normalized_cors_origins_keeps_non_loopback_origins(self) -> None:
        settings = Settings(cors_allow_origins=["https://roundzero.ai"])

        self.assertEqual(settings.normalized_cors_origins(), ["https://roundzero.ai"])

    def test_normalized_cors_origins_uses_local_defaults_when_empty(self) -> None:
        settings = Settings(cors_allow_origins=[])

        self.assertEqual(settings.normalized_cors_origins(), LOCAL_DEV_ORIGINS)


if __name__ == "__main__":
    unittest.main()
