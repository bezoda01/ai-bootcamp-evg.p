from __future__ import annotations

import unittest

from authservice_qa_mcp.safety import normalize_select_sql, validate_container_name, validate_lines


class SafetyTests(unittest.TestCase):
    def test_normalize_select_sql_allows_single_read_query(self) -> None:
        self.assertEqual(
            normalize_select_sql("-- inspect user\nSELECT id, email FROM users;", 1000),
            "SELECT id, email FROM users",
        )

    def test_normalize_select_sql_allows_read_only_cte(self) -> None:
        sql = "WITH active_users AS (SELECT id FROM users WHERE status = 'active') SELECT * FROM active_users"

        self.assertEqual(normalize_select_sql(sql, 1000), sql)

    def test_normalize_select_sql_blocks_stacked_statements(self) -> None:
        with self.assertRaisesRegex(ValueError, "semicolon-separated"):
            normalize_select_sql("SELECT * FROM users; SELECT * FROM users", 1000)

    def test_normalize_select_sql_blocks_mutating_keywords(self) -> None:
        with self.assertRaisesRegex(ValueError, "blocked SQL keyword"):
            normalize_select_sql("SELECT * FROM users WHERE id IN (DELETE FROM users)", 1000)

    def test_validate_container_name_rejects_shell_metacharacters(self) -> None:
        with self.assertRaises(ValueError):
            validate_container_name("auth-service;rm -rf /")

    def test_validate_lines_enforces_configured_maximum(self) -> None:
        with self.assertRaisesRegex(ValueError, "<= 100"):
            validate_lines(101, 100)


if __name__ == "__main__":
    unittest.main()
