from django.test import TestCase, override_settings
from django.urls import reverse
from django.core import mail
from django.contrib.auth import get_user_model


class RegistrationEmailTests(TestCase):
    def test_registration_sends_confirmation_email(self):
        url = reverse('register')
        data = {
            'username': 'newuser',
            'email': 'newuser@example.com',
            'phone': '',
            'password1': 'strong-pass-123',
            'password2': 'strong-pass-123',
        }

        # Ensure no emails before
        mail.outbox = []
        response = self.client.post(url, data)
        # After successful registration should redirect (we redirect to home)
        self.assertEqual(response.status_code, 302)

        # User created but inactive until confirmation
        User = get_user_model()
        user_qs = User.objects.filter(email='newuser@example.com')
        self.assertTrue(user_qs.exists())
        user = user_qs.first()
        self.assertFalse(user.is_active)

        # Exactly one email sent
        self.assertEqual(len(mail.outbox), 1)
        message = mail.outbox[0]
        self.assertIn('Confirma tu correo', message.subject)

        # The email should contain an activation link with uidb64 and token
        body = message.body if getattr(message, 'body', None) else ''
        alt = ''
        if getattr(message, 'alternatives', None):
            try:
                alt = message.alternatives[0][0]
            except Exception:
                alt = ''
        content = body + alt
        self.assertIn('confirm', content)

        # Extract activation link from the email and simulate visiting it
        import re
        m = re.search(r'https?://[^\s\n>]+/confirm/([A-Za-z0-9_\-]+)/([A-Za-z0-9\-]+)', content)
        self.assertIsNotNone(m, msg='Activation link not found in email')
        uidb64 = m.group(1)
        token = m.group(2)

        # Visit activation URL
        activation_url = reverse('confirm_email', args=[uidb64, token])
        resp = self.client.get(activation_url)
        # After activation user should be active
        user.refresh_from_db()
        self.assertTrue(user.is_active)
