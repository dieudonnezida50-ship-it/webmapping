import json
from django.contrib.auth.models import Group, User
from django.contrib.gis.geos import GEOSGeometry
from django.test import TestCase, override_settings
from django.urls import reverse

from .models import (
    Commune, Secteur, TypeEquipement, EtatPhysique, StatutFonctionnement,
    Equipement, DetailsEclairage, DetailsAdministration
)


@override_settings(ALLOWED_HOSTS=['testserver', 'localhost'])
class EquipementFormTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpass')
        agent_group, _ = Group.objects.get_or_create(name='Agent')
        self.user.groups.add(agent_group)
        self.user.save()

        self.commune = Commune.objects.create(
            nom='Commune Test',
            geom=GEOSGeometry('POLYGON((0 0, 0 1, 1 1, 1 0, 0 0))', srid=4326),
            superficie=1.0
        )
        self.secteur = Secteur.objects.create(
            nom='Secteur Test',
            commune=self.commune,
            geom=GEOSGeometry('POLYGON((0 0, 0 0.5, 0.5 0.5, 0.5 0, 0 0))', srid=4326),
            superficie=0.25
        )
        self.type_equipement = TypeEquipement.objects.create(libelle='Éclairage public', icone='fa-lightbulb')
        self.etat = EtatPhysique.objects.create(libelle='Neuf')
        self.statut = StatutFonctionnement.objects.create(libelle='Opérationnel')

    def test_ajouter_equipement_creates_equipment_and_details(self):
        self.client.force_login(self.user)
        url = reverse('ajouter_equipement')

        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        data = {
            'nom': 'Lampadaire Test',
            'code_identification': 'ECL-001',
            'type_equipement': self.type_equipement.pk,
            'secteur': self.secteur.pk,
            'annee_realisation': 2025,
            'accessibilite': 'Libre',
            'etat': self.etat.pk,
            'statut': self.statut.pk,
            'latitude': 12.345678,
            'longitude': -1.234567,
            'type_technologie': 'LED',
            'nombre_foyers': 8,
            'puissance_lampe': 150,
            'hauteur_poteau': 9.5,
        }

        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Equipement.objects.filter(code_identification='ECL-001').exists())

        equipement = Equipement.objects.get(code_identification='ECL-001')
        self.assertEqual(equipement.nom, 'Lampadaire Test')
        self.assertEqual(equipement.type_equipement, self.type_equipement)
        self.assertEqual(equipement.statut, self.statut)
        self.assertEqual(equipement.etat, self.etat)
        self.assertIsNotNone(equipement.localisation)
        self.assertTrue(hasattr(equipement, 'details_eclairage'))

        details = equipement.details_eclairage
        self.assertEqual(details.type_technologie, 'LED')
        self.assertEqual(details.nombre_foyers, 8)
        self.assertEqual(details.puissance_lampe, 150)
        self.assertEqual(details.hauteur_poteau, 9.5)

    def test_modifier_equipement_prefills_type_specific_details(self):
        self.client.force_login(self.user)
        equipement = Equipement.objects.create(
            nom='Lampadaire Edition',
            code_identification='ECL-EDIT',
            type_equipement=self.type_equipement,
            secteur=self.secteur,
            annee_realisation=2024,
            accessibilite='Libre',
            etat=self.etat,
            statut=self.statut,
            localisation=GEOSGeometry('POINT(-1.234567 12.345678)', srid=4326),
            cree_par=self.user
        )
        details = DetailsEclairage.objects.create(
            equipement=equipement,
            type_technologie='LED',
            nombre_foyers=10,
            puissance_lampe=120,
            hauteur_poteau=8.5
        )

        response = self.client.get(reverse('modifier_equipement', args=[equipement.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertIn('form_details', response.context)
        self.assertIsNotNone(response.context['form_details'])
        self.assertEqual(response.context['form_details'].instance, details)
        self.assertContains(response, 'LED')

    def test_equipements_geojson_includes_details(self):
        self.client.force_login(self.user)
        equipement = Equipement.objects.create(
            nom='Lampadaire API',
            code_identification='ECL-API',
            type_equipement=self.type_equipement,
            secteur=self.secteur,
            annee_realisation=2025,
            accessibilite='Libre',
            etat=self.etat,
            statut=self.statut,
            localisation=GEOSGeometry('POINT(-1.234567 12.345678)', srid=4326)
        )
        DetailsEclairage.objects.create(
            equipement=equipement,
            type_technologie='LED',
            nombre_foyers=12,
            puissance_lampe=200,
            hauteur_poteau=10.0
        )

        response = self.client.get(reverse('api_equipements'))
        self.assertEqual(response.status_code, 200)

        data = response.json()
        self.assertIn('features', data)
        feature = next((f for f in data['features'] if f['properties'].get('code_identification') == 'ECL-API'), None)
        self.assertIsNotNone(feature)
        self.assertIn('details', feature['properties'])
        self.assertEqual(feature['properties']['details']['type_technologie'], 'LED')
        self.assertEqual(feature['properties']['details']['nombre_foyers'], 12)
        self.assertEqual(feature['properties']['details']['puissance_lampe'], 200)
        self.assertEqual(feature['properties']['details']['hauteur_poteau'], 10.0)

    def test_equipements_geojson_includes_administration_details(self):
        self.client.force_login(self.user)
        equipement = Equipement.objects.create(
            nom='Commissariat API',
            code_identification='ADM-API',
            type_equipement=self.type_equipement,
            secteur=self.secteur,
            annee_realisation=2025,
            accessibilite='Libre',
            etat=self.etat,
            statut=self.statut,
            localisation=GEOSGeometry('POINT(-1.234567 12.345678)', srid=4326)
        )
        DetailsAdministration.objects.create(
            equipement=equipement,
            type_administration='Commissariat',
            nombre_bureaux=5,
            salle_reunion=True,
            accessible_public=True
        )

        response = self.client.get(reverse('api_equipements'))
        self.assertEqual(response.status_code, 200)

        data = response.json()
        self.assertIn('features', data)
        feature = next((f for f in data['features'] if f['properties'].get('code_identification') == 'ADM-API'), None)
        self.assertIsNotNone(feature)
        self.assertIn('details', feature['properties'])
        self.assertEqual(feature['properties']['details']['type_administration'], 'Commissariat')
        self.assertEqual(feature['properties']['details']['nombre_bureaux'], 5)
        self.assertEqual(feature['properties']['details']['salle_reunion'], True)
        self.assertEqual(feature['properties']['details']['accessible_public'], True)
