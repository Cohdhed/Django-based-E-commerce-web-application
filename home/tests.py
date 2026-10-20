from django.test import TestCase
from django.urls import reverse

from home.models import Contact
from userprofile.tests import make_phone


class CatalogueTests(TestCase):
    def setUp(self):
        for i in range(10):
            make_phone(name=f'Phone {i}', price=1000 + i, featured=(i == 0))

    def test_pagination_search_and_sort(self):
        r = self.client.get(reverse('products'))
        self.assertEqual(len(r.context['pagin']), 8)
        r = self.client.get(reverse('products'), {'q': 'phone 3'})
        self.assertEqual(r.context['pagin'].paginator.count, 1)
        r = self.client.get(reverse('products'), {'sort': 'price_desc'})
        self.assertEqual(r.context['pagin'][0].name, 'Phone 9')
        r = self.client.get(reverse('products'), {'sort': '; DROP TABLE'})
        self.assertEqual(r.status_code, 200)

    def test_empty_search_shows_message(self):
        self.assertContains(self.client.get(reverse('products'), {'q': 'zzz'}), 'No phones found')

    def test_bad_ids_are_404_not_500(self):
        self.assertEqual(self.client.get(reverse('detail', args=[9999, 'x'])).status_code, 404)
        self.assertEqual(self.client.get(reverse('category', args=[9999, 'x'])).status_code, 404)
        self.assertEqual(self.client.get('/nope/').status_code, 404)

    def test_home_without_company_profile_renders(self):
        self.assertContains(self.client.get(reverse('home')), 'Featured phones')

    def test_contact_form_saves_and_validates(self):
        self.assertEqual(self.client.post(reverse('contact'), {'first_name': 'A'}).status_code, 200)
        self.assertEqual(Contact.objects.count(), 0)
        r = self.client.post(reverse('contact'), {'first_name': 'A', 'last_name': 'B', 'email': 'a@b.co', 'message': 'hi'})
        self.assertRedirects(r, reverse('home'))
        self.assertEqual(Contact.objects.count(), 1)
