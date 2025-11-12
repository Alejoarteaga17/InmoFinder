from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from .models import Propiedad, ContactMessage


class ContactRequestTests(TestCase):
	def setUp(self):
		User = get_user_model()
		# owner of the property
		self.owner = User.objects.create_user(username='owner', email='owner@example.com', password='pass')
		# sender (authenticated user who will send contact)
		self.sender = User.objects.create_user(username='sender', email='sender@example.com', password='pass')

		# create a property
		self.prop = Propiedad.objects.create(
			owner=self.owner,
			title='Test Property',
			location='Test Location',
			area_m2=10,
			area_privada_m2=8,
			rooms=1,
			bathrooms=1,
			parking_spaces=0,
			floor=1,
			price_cop=100000,
		)

	def test_contact_request_is_saved(self):
		# login as sender (custom user model uses email as USERNAME_FIELD)
		login = self.client.login(email='sender@example.com', password='pass')
		self.assertTrue(login)

		url = reverse('contact_owner', args=[self.prop.id])
		data = {
			'nombre': 'Sender Name',
			'email': 'sender@example.com',
			'telefono': '123456',
			'mensaje': 'Hello, I am interested.'
		}

		# simulate AJAX request
		response = self.client.post(url, data, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
		self.assertEqual(response.status_code, 200)
		json = response.json()
		self.assertTrue(json.get('success'))

		# verify ContactMessage saved
		cm_qs = ContactMessage.objects.filter(propiedad=self.prop, user=self.sender)
		self.assertTrue(cm_qs.exists(), 'ContactMessage was not created')
		cm = cm_qs.first()
		self.assertEqual(cm.mensaje, data['mensaje'])
		self.assertEqual(cm.email, data['email'])
		self.assertEqual(cm.nombre, data['nombre'])
		self.assertIsNotNone(cm.fecha_envio)
