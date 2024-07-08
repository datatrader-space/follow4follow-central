from django.test import TestCase

# Create your tests here.
from django.test import TestCase, Client
from .views import createResource

class CreateDeviceViewTest(TestCase):
    def test_create_device_success(self):
        client = Client()
        response = client.post('/api/resource/create/', {'name': 'Test Device'})
        print(response.content)
        #print(response.request)
        #self.assertEqual(response.status_code, 200)  # 201 Created

        # Additional assertions to check response content, database changes, etc.
