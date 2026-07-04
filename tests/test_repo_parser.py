import unittest

from code_manager.domain.repo_parser import parse_repository_url


class ParseRepositoryUrlTests(unittest.TestCase):
    def test_parses_https_repository_url(self) -> None:
        result = parse_repository_url("https://git.example.com/platform/order-service.git")

        self.assertEqual(result.group_english_name, "platform")
        self.assertEqual(result.local_dir_name, "order-service")
        self.assertEqual(result.app_name, "order-service")

    def test_parses_ssh_repository_url(self) -> None:
        result = parse_repository_url("git@git.example.com:business/payment-api.git")

        self.assertEqual(result.group_english_name, "business")
        self.assertEqual(result.local_dir_name, "payment-api")
        self.assertEqual(result.app_name, "payment-api")

    def test_rejects_repository_without_group(self) -> None:
        with self.assertRaises(ValueError):
            parse_repository_url("https://git.example.com/no-group.git")


if __name__ == "__main__":
    unittest.main()
