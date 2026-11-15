from anymail.backends.resend import EmailBackend as AnymailResendBackend


class ResendEmailBackend(AnymailResendBackend):
    """Expose Resend API failures as delivery errors handled by RoomFinder."""

    def send_messages(self, email_messages):
        try:
            return super().send_messages(email_messages)
        except Exception as exc:
            raise RuntimeError("Resend API email delivery failed") from exc
