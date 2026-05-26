import unittest

from app.email_processing import NormalizedAttachment, NormalizedEmail


class EmailProcessingTestCase(unittest.TestCase):
    def test_to_analysis_text_includes_extracted_attachment_text(self):
        email = NormalizedEmail(
            subject="Договор",
            sender="sender@example.com",
            recipients=["user@example.com"],
            body_text="Смотрите вложение.",
            source_name="contract.eml",
            attachments=[
                NormalizedAttachment(
                    filename="notes.txt",
                    content_type="text/plain",
                    size_bytes=42,
                    extracted_text="Согласовать до пятницы.",
                )
            ],
        )

        result = email.to_analysis_text()

        self.assertIn("notes.txt", result)
        self.assertIn("Текст вложения: Согласовать до пятницы.", result)

    def test_has_extractable_content_accepts_attachment_text_without_body(self):
        email = NormalizedEmail(
            subject="Договор",
            sender="sender@example.com",
            recipients=[],
            body_text="   ",
            source_name="contract.eml",
            attachments=[
                NormalizedAttachment(
                    filename="notes.txt",
                    content_type="text/plain",
                    size_bytes=42,
                    extracted_text="Есть полезный текст.",
                )
            ],
        )

        self.assertTrue(email.has_extractable_content())

    def test_has_extractable_content_rejects_empty_body_and_empty_attachments(self):
        email = NormalizedEmail(
            subject="empty",
            sender="unknown",
            recipients=[],
            body_text="   ",
            source_name="empty.txt",
        )

        self.assertFalse(email.has_extractable_content())


if __name__ == "__main__":
    unittest.main()
