from django import forms
from django.contrib.gis.geos import GEOSGeometry, Point  # Indispensable pour la manipulation spatiale PostGIS
from django.contrib.auth.models import Group, User
from .models import (
    Commune, Equipement, Secteur, EtatPhysique, StatutFonctionnement,
    DetailsEcole, DetailsSante, DetailsForage, DetailsMarche, 
    DetailsAdministration, DetailsAssainissement, DetailsSport, DetailsEclairage
)


# =====================================================================
# 1. FORMULAIRE CENTRAL : ÉQUIPEMENT (AVEC SAISIE MANUELLE LAT/LON)
# =====================================================================
class EquipementForm(forms.ModelForm):
    # Ajout de champs virtuels (non liés directement au modèle mais utiles pour la saisie manuelle)
    latitude = forms.FloatField(
        required=False,
        label="Latitude",
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Ex: 12.3714', 'step': 'any'})
    )
    longitude = forms.FloatField(
        required=False,
        label="Longitude",
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Ex: -1.5197', 'step': 'any'})
    )

    class Meta:
        model = Equipement
        # Liste des champs à afficher
        fields = [
            'nom', 'code_identification', 'type_equipement', \
            'secteur', 'annee_realisation', 'accessibilite', \
            'etat', 'statut', 'localisation'
        ]
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Le champ localisation est généré via latitude/longitude ou la géométrie brute,
        # il ne doit pas être requis au niveau du formulaire HTML.
        self.fields['localisation'].required = False
        self.fields['localisation'].widget = forms.HiddenInput(attrs={
            'id': 'id_localisation',
            'class': 'form-control font-monospace bg-light',
            'readonly': 'readonly',
            'placeholder': 'Géométrie capturée automatiquement via la carte'
        })

        # Si on modifie un équipement existant, on extrait la lat/lon depuis PostGIS pour pré-remplir les champs numériques
        if self.instance and self.instance.pk and self.instance.localisation:
            self.fields['longitude'].initial = self.instance.localisation.x
            self.fields['latitude'].initial = self.instance.localisation.y

        # Application du style professionnel Bootstrap 5
        for field_name, field in self.fields.items():
            if field_name == 'localisation':
                continue
            elif isinstance(field.widget, forms.Select):
                field.widget.attrs.update({'class': 'form-select'})
            elif isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs.update({'class': 'form-check-input'})
            else:
                field.widget.attrs.update({'class': 'form-control'})

    def clean(self):
        cleaned_data = super().clean()
        lat = cleaned_data.get('latitude')
        lon = cleaned_data.get('longitude')
        localisation_str = cleaned_data.get('localisation')

        # REGLE DE VALIDATION : Priorité à la saisie de la latitude et longitude numérique
        if lat is not None and lon is not None:
            try:
                # Création de l'objet spatial Point(X=longitude, Y=latitude) avec le SRID WGS84
                cleaned_data['localisation'] = Point(lon, lat, srid=4326)
            except Exception as e:
                raise forms.ValidationError(f"Erreur lors de la conversion des coordonnées : {e}")
        
        # Si l'utilisateur n'a pas rempli la Lat/Lon mais qu'il y a une chaîne de texte venant de la carte Leaflet
        elif isinstance(localisation_str, str) and localisation_str.strip():
            try:
                cleaned_data['localisation'] = GEOSGeometry(localisation_str)
            except Exception as e:
                raise forms.ValidationError(f"Format de géométrie cartographique invalide : {e}")
                
        # Si aucun des deux moyens n'est fourni
        elif not cleaned_data.get('localisation'):
            raise forms.ValidationError("Veuillez soit saisir manuellement la latitude et la longitude, soit cliquer sur la carte.")

        return cleaned_data


# =====================================================================
# 2. FORMULAIRE D'EXTENSION : DÉTAILS DES 8 INFRASTRUCTURES MÉTIERS
# =====================================================================

class EcoleForm(forms.ModelForm):
    class Meta:
        model = DetailsEcole
        exclude = ['equipement']
        widgets = {
            'nombre_classes': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Ex: 6'}),
            'nombre_eleves': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Ex: 320'}),
            'nombre_enseignants': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Ex: 8'}),
            'cycle_enseignement': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: Primaire, Secondaire'}),
            'presence_cantine': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'nom_directeur': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nom et Prénom du gestionnaire'}),
        }


class SanteForm(forms.ModelForm):
    class Meta:
        model = DetailsSante
        exclude = ['equipement']
        widgets = {
            'type_centre': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: CSPS, CM, CHR'}),
            'capacite_lits': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Ex: 15'}),
            'presence_maternite': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'ambulance_fonctionnelle': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'personnel_medical_count': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Ex: 5'}),
        }


class ForageForm(forms.ModelForm):
    class Meta:
        model = DetailsForage
        exclude = ['equipement']
        widgets = {
            'type_pompe': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: Pompe Volanta, India, Solaire'}),
            'profondeur': forms.NumberInput(attrs={'class': 'form-control', 'step': 'any', 'placeholder': 'En mètres (Ex: 45.5)'}),
            'debit': forms.NumberInput(attrs={'class': 'form-control', 'step': 'any', 'placeholder': 'En m³/h (Ex: 2.5)'}),
            'population_desservie': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Ex: 500'}),
            'mode_gestion': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: Communautaire, Privé, Association'}),
        }


class MarcheForm(forms.ModelForm):
    class Meta:
        model = DetailsMarche
        exclude = ['equipement']
        widgets = {
            'nombre_boutiques': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Ex: 40'}),
            'superficie': forms.NumberInput(attrs={'class': 'form-control', 'step': 'any', 'placeholder': 'En m²'}),
            'frequence_marche': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: Hebdomadaire, Quotidien'}),
            'cloture': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class AdministrationForm(forms.ModelForm):
    class Meta:
        model = DetailsAdministration
        exclude = ['equipement']
        widgets = {
            'type_administration': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: Mairie, Préfecture, Commissariat'}),
            'nombre_bureaux': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Ex: 12'}),
            'salle_reunion': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'accessible_public': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class AssainissementForm(forms.ModelForm):
    class Meta:
        model = DetailsAssainissement
        exclude = ['equipement']
        widgets = {
            'type_ouvrage': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: Caniveau, Latrine publique, Bassin'}),
            'longueur_reseau': forms.NumberInput(attrs={'class': 'form-control', 'step': 'any', 'placeholder': 'En mètres'}),
            'dimension_capacite': forms.NumberInput(attrs={'class': 'form-control', 'step': 'any', 'placeholder': 'En m³'}),
            'nature_reseau': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: Béton armé, Maçonnerie, Enterré'}),
        }


class SportForm(forms.ModelForm):
    class Meta:
        model = DetailsSport
        exclude = ['equipement']
        widgets = {
            'nature_sport': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: Terrain de Football, Plateau Omnisport'}),
            'nature_revetement': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: Terre battue, Gazon synthétique, Bitume'}),
            'presence_eclairage': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'capacite_places': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Nombre de places assises'}),
        }


class EclairageForm(forms.ModelForm):
    class Meta:
        model = DetailsEclairage
        exclude = ['equipement']
        widgets = {
            'type_technologie': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: Lampadaire Solaire LED, Réseau SONABEL'}),
            'nombre_foyers': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Ex: 25'}),
            'puissance_lampe': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'En Watts (Ex: 60)'}),
            'hauteur_poteau': forms.NumberInput(attrs={'class': 'form-control', 'step': 'any', 'placeholder': 'En mètres (Ex: 8)'}),
        }


# =====================================================================
# 3. FORMULAIRE COMMUNE
# =====================================================================
class CommuneForm(forms.ModelForm):
    # Champs virtuels pour saisie manuelle de latitude/longitude
    latitude = forms.FloatField(
        required=False,
        label="Latitude du centre",
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Ex: 12.3714', 'step': 'any'})
    )
    longitude = forms.FloatField(
        required=False,
        label="Longitude du centre",
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Ex: -1.5197', 'step': 'any'})
    )
    # Champ pour importer un fichier (CSV ou GeoJSON)
    fichier_import = forms.FileField(
        required=False,
        label="Importer depuis un fichier (CSV ou GeoJSON)",
        widget=forms.FileInput(attrs={'class': 'form-control', 'accept': '.csv,.geojson,.json'})
    )
    
    class Meta:
        model = Commune
        fields = ['nom', 'code_insee', 'population', 'superficie', 'geom', 'latitude', 'longitude']
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Gérer le champ geom
        self.fields['geom'].required = False
        self.fields['geom'].widget = forms.HiddenInput(attrs={
            'class': 'form-control font-monospace bg-light',
            'id': 'id_geom',
            'placeholder': 'Tracez le polygone sur la carte pour capturer les frontières'
        })
        
        # Champ superficie en lecture seule
        self.fields['superficie'].widget.attrs.update({
            'class': 'form-control bg-light',
            'readonly': 'readonly',
            'placeholder': 'Calculée automatiquement en Ha'
        })
        
        # Si on modifie une commune existante, pré-remplir lat/lon
        if self.instance and self.instance.pk:
            if self.instance.latitude:
                self.fields['latitude'].initial = self.instance.latitude
            if self.instance.longitude:
                self.fields['longitude'].initial = self.instance.longitude
        
        # Style Bootstrap
        for field_name, field in self.fields.items():
            if field_name not in ['geom', 'fichier_import']:
                if field_name == 'superficie':
                    continue
                if isinstance(field.widget, forms.Select):
                    field.widget.attrs.update({'class': 'form-select'})
                else:
                    field.widget.attrs.update({'class': 'form-control'})

    def clean(self):
        cleaned_data = super().clean()
        # Les validations se feront dans la view pour gérer l'import de fichier
        return cleaned_data

    def clean_geom(self):
        geom_data = self.cleaned_data.get('geom')
        if isinstance(geom_data, str) and geom_data.strip():
            try:
                return GEOSGeometry(geom_data)
            except Exception as e:
                raise forms.ValidationError(f"Géométrie commune invalide : {e}")
        return geom_data


# =====================================================================
# 4. FORMULAIRE SECTEUR
# =====================================================================
class SecteurForm(forms.ModelForm):
    # Champs virtuels pour saisie manuelle de latitude/longitude
    latitude = forms.FloatField(
        required=False,
        label="Latitude du centre",
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Ex: 12.3714', 'step': 'any'})
    )
    longitude = forms.FloatField(
        required=False,
        label="Longitude du centre",
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Ex: -1.5197', 'step': 'any'})
    )
    # Champ pour importer un fichier (CSV ou GeoJSON)
    fichier_import = forms.FileField(
        required=False,
        label="Importer depuis un fichier (CSV ou GeoJSON)",
        widget=forms.FileInput(attrs={'class': 'form-control', 'accept': '.csv,.geojson,.json'})
    )
    
    class Meta:
        model = Secteur
        fields = ['nom', 'commune', 'geom', 'latitude', 'longitude']
        
        widgets = {
            'nom': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Exemple : Secteur 01, Quartier Zongo...',
                'required': 'required'
            }),
            'commune': forms.Select(attrs={
                'class': 'form-select',
                'id': 'id_commune_select',
                'required': 'required'
            }),
            'geom': forms.Textarea(attrs={
                'class': 'form-control font-monospace bg-light',
                'id': 'id_geom',
                'style': 'height: 60px;',
                'placeholder': 'Géométrie capturée automatiquement depuis la carte'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Geom pas requis au niveau du formulaire
        self.fields['geom'].required = False
        
        # Si on modifie un secteur existant, pré-remplir lat/lon
        if self.instance and self.instance.pk:
            if self.instance.latitude:
                self.fields['latitude'].initial = self.instance.latitude
            if self.instance.longitude:
                self.fields['longitude'].initial = self.instance.longitude

    def clean_geom(self):
        geom_data = self.cleaned_data.get('geom')
        if isinstance(geom_data, str) and geom_data.strip():
            try:
                return GEOSGeometry(geom_data)
            except Exception as e:
                raise forms.ValidationError(f"Géométrie secteur invalide : {e}")
        return geom_data


# =====================================================================
# 5. FORMULAIRES DE CONFIGURATION (NOMENCLATURES)
# =====================================================================
class EtatPhysiqueForm(forms.ModelForm):
    class Meta:
        model = EtatPhysique
        fields = ['libelle']
        widgets = {
            'libelle': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Exemple : Excellent, Bon état, Très dégradé...',
                'required': 'required'
            }),
        }

class StatutFonctionnementForm(forms.ModelForm):
    class Meta:
        model = StatutFonctionnement
        fields = ['libelle']
        widgets = {
            'libelle': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ex: Opérationnel, En maintenance, En panne...'
            }),
        }


# =====================================================================
# 6. GESTION DES UTILISATEURS / AGENTS (SUPERADMIN ONLY)
# =====================================================================
class UtilisateurCreationForm(forms.ModelForm):
    mot_de_passe = forms.CharField(
        label="Mot de passe",
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Entrez le mot de passe'}),
        help_text="Obligatoire pour la création du compte."
    )
    role = forms.ModelChoiceField(
        queryset=Group.objects.all(),
        label="Rôle / Groupe",
        widget=forms.Select(attrs={'class': 'form-select'}),
        empty_label="Sélectionnez un rôle"
    )

    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email', 'is_active']
        labels = {
            'username': "Nom d'utilisateur (Identifiant unique)",
            'first_name': "Prénom",
            'last_name': "Nom de famille",
            'email': "Adresse email",
            'is_active': "Activer le compte immédiatement"
        }
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control', 'placeholder': "Ex: amadou_traore"}),
            'first_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': "Ex: Amadou"}),
            'last_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': "Ex: Traoré"}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': "Ex: agent@commune.bf"}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["mot_de_passe"])
        if commit:
            user.save()
            groupe = self.cleaned_data.get('role')
            if groupe:
                user.groups.add(groupe)
        return user


class UtilisateurModificationForm(forms.ModelForm):
    nouveau_mot_de_passe = forms.CharField(
        label="Changer le mot de passe",
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Laissez vide pour ne pas modifier'}),
        required=False,
        help_text="Remplissez ce champ uniquement si vous souhaitez modifier son mot de passe actuel."
    )
    role = forms.ModelChoiceField(
        queryset=Group.objects.all(),
        label="Rôle / Groupe",
        widget=forms.Select(attrs={'class': 'form-select'}),
        empty_label="Sélectionnez un rôle"
    )

    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email', 'is_active']
        labels = {
            'username': "Nom d'utilisateur",
            'first_name': "Prénom",
            'last_name': "Nom",
            'email': "Adresse Email",
            'is_active': "Compte actif"
        }
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            groupe_actuel = self.instance.groups.first()
            if groupe_actuel:
                self.fields['role'].initial = groupe_actuel.id

    def save(self, commit=True):
        user = super().save(commit=False)
        nouveau_mdp = self.cleaned_data.get("nouveau_mot_de_passe")
        if nouveau_mdp:
            user.set_password(nouveau_mdp)
        
        if commit:
            user.save()
            user.groups.clear()
            groupe = self.cleaned_data.get('role')
            if groupe:
                user.groups.add(groupe)
        return user
    
    
    # =====================================================================
# 2. FORMULAIRES SPÉCIFIQUES MÉTIERS (DÉTAILS DES INFRASTRUCTURES)
# =====================================================================

class DetailsEcoleForm(forms.ModelForm):
    class Meta:
        model = DetailsEcole
        exclude = ['equipement']  # On exclut le lien vers l'équipement car il est géré dynamiquement dans la vue

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            widget = field.widget
            if isinstance(widget, forms.CheckboxInput):
                widget.attrs.update({'class': 'form-check-input'})
            elif isinstance(widget, forms.Select):
                widget.attrs.update({'class': 'form-select'})
            else:
                widget.attrs.update({'class': 'form-control'})


class DetailsSanteForm(forms.ModelForm):
    class Meta:
        model = DetailsSante
        exclude = ['equipement']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            widget = field.widget
            if isinstance(widget, forms.CheckboxInput):
                widget.attrs.update({'class': 'form-check-input'})
            elif isinstance(widget, forms.Select):
                widget.attrs.update({'class': 'form-select'})
            else:
                widget.attrs.update({'class': 'form-control'})


class DetailsForageForm(forms.ModelForm):
    class Meta:
        model = DetailsForage
        exclude = ['equipement']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            widget = field.widget
            if isinstance(widget, forms.CheckboxInput):
                widget.attrs.update({'class': 'form-check-input'})
            elif isinstance(widget, forms.Select):
                widget.attrs.update({'class': 'form-select'})
            else:
                widget.attrs.update({'class': 'form-control'})


class DetailsMarcheForm(forms.ModelForm):
    class Meta:
        model = DetailsMarche
        exclude = ['equipement']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            widget = field.widget
            if isinstance(widget, forms.CheckboxInput):
                widget.attrs.update({'class': 'form-check-input'})
            elif isinstance(widget, forms.Select):
                widget.attrs.update({'class': 'form-select'})
            else:
                widget.attrs.update({'class': 'form-control'})


class DetailsAdministrationForm(forms.ModelForm):
    class Meta:
        model = DetailsAdministration
        exclude = ['equipement']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            widget = field.widget
            if isinstance(widget, forms.CheckboxInput):
                widget.attrs.update({'class': 'form-check-input'})
            elif isinstance(widget, forms.Select):
                widget.attrs.update({'class': 'form-select'})
            else:
                widget.attrs.update({'class': 'form-control'})


class DetailsAssainissementForm(forms.ModelForm):
    class Meta:
        model = DetailsAssainissement
        exclude = ['equipement']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            widget = field.widget
            if isinstance(widget, forms.CheckboxInput):
                widget.attrs.update({'class': 'form-check-input'})
            elif isinstance(widget, forms.Select):
                widget.attrs.update({'class': 'form-select'})
            else:
                widget.attrs.update({'class': 'form-control'})


class DetailsSportForm(forms.ModelForm):
    class Meta:
        model = DetailsSport
        exclude = ['equipement']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            widget = field.widget
            if isinstance(widget, forms.CheckboxInput):
                widget.attrs.update({'class': 'form-check-input'})
            elif isinstance(widget, forms.Select):
                widget.attrs.update({'class': 'form-select'})
            else:
                widget.attrs.update({'class': 'form-control'})


class DetailsEclairageForm(forms.ModelForm):
    class Meta:
        model = DetailsEclairage
        exclude = ['equipement']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            widget = field.widget
            if isinstance(widget, forms.CheckboxInput):
                widget.attrs.update({'class': 'form-check-input'})
            elif isinstance(widget, forms.Select):
                widget.attrs.update({'class': 'form-select'})
            else:
                widget.attrs.update({'class': 'form-control'})