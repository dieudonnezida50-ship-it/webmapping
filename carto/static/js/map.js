// ==========================================================
// 📄 static/js/map.js - CONFIGURATION VISITEUR PREMIUM
// ==========================================================

const map = L.map('map').setView([12.3714, -1.5197], 12);

const osmLayer = L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    maxZoom: 19,
    attribution: '© OpenStreetMap contributors'
}).addTo(map);

const communeLayer = L.layerGroup().addTo(map);
const secteursLayer = L.layerGroup().addTo(map);
const equipementsLayer = L.layerGroup().addTo(map);

let allEquipementsData = null;

const baseMaps = { "Fond de carte OSM": osmLayer };
const overlayMaps = {
    "📍 Équipements Communaux": equipementsLayer,
    "🟩 Découpage Secteurs": secteursLayer,
    "🗺️ Limite Administrative": communeLayer
};

L.control.layers(baseMaps, overlayMaps, { collapsed: false, position: 'topright' }).addTo(map);
// MODIFICATION POUR RENDRE LES ICÔNES ET COULEURS DYNAMIQUES DEPUIS DJANGO
function getStyleByType(type, featureProperties) {
    // Si Django fournit une couleur et une icône spécifiques pour cet équipement (via la BD), on les utilise en priorité
    if (featureProperties && featureProperties.marker_color && featureProperties.icone) {
        return { 
            color: featureProperties.marker_color, 
            icon: featureProperties.icone 
        };
    }

    // [Système de secours / Fallback] Si la base de données est vide, on garde votre ancienne logique textuelle
    let typeLower = (type || "").toLowerCase();
    if (typeLower.includes("école") || typeLower.includes("scolaire") || typeLower.includes("enseign")) {
        return { color: "#e67e22", icon: "fa-graduation-cap" };
    } else if (typeLower.includes("forage") || typeLower.includes("eau") || typeLower.includes("puits") || typeLower.includes("fontaine")) {
        return { color: "#2980b9", icon: "fa-faucet" };
    } else if (typeLower.includes("santé") || typeLower.includes("dispensaire") || typeLower.includes("hôpital") || typeLower.includes("csps")) {
        return { color: "#e74c3c", icon: "fa-house-medical" };
    } else if (typeLower.includes("marché") || typeLower.includes("commerce") || typeLower.includes("boutique")) {
        return { color: "#27ae60", icon: "fa-shop" };
    }
    return { color: "#34495e", icon: "fa-building" };
}

function getIconForEquipement(type, featureProperties) {
    // On passe désormais l'objet complet des propriétés à la fonction de style
    let style = getStyleByType(type, featureProperties);
    return L.divIcon({
        html: `
            <div style="background-color: ${style.color}; width: 32px; height: 32px; border-radius: 50% 50% 50% 0; transform: rotate(-45deg); display: flex; align-items: center; justify-content: center; border: 2px solid #fff; box-shadow: 0 3px 8px rgba(0,0,0,0.3);">
                <i class="fa-solid ${style.icon}" style="transform: rotate(45deg); color: white; font-size: 12px;"></i>
            </div>
        `,
        className: "", iconSize: [32, 32], iconAnchor: [16, 32], popupAnchor: [0, -32]
    });
}

function getStatusBadge(statut) {
    let statutLower = (statut || "").toLowerCase();
    let color = "#f39c12";
    if (statutLower.includes("opérationnel") || statutLower.includes("bon") || statutLower.includes("marche")) color = "#27ae60";
    else if (statutLower.includes("panne") || statutLower.includes("arrêt") || statutLower.includes("mauvais")) color = "#c0392b";
    
    return `<span style="background-color: ${color}; color: white; padding: 3px 10px; border-radius: 20px; font-weight: 600; font-size: 11px; text-transform: uppercase;">${statut}</span>`;
}

const detailFieldLabels = {
    type_technologie: "Type de technologie",
    nombre_foyers: "Nombre de foyers",
    puissance_lampe: "Puissance de la lampe (W)",
    hauteur_poteau: "Hauteur du poteau (m)",
    presence_cantine: "Présence d'une cantine",
    presence_maternite: "Présence d'une maternité",
    ambulance_fonctionnelle: "Ambulance fonctionnelle",
    cloture: "Marché clôturé",
    salle_reunion: "Présence d'une salle de réunion",
    accessible_public: "Accessible au public (PMR)",
    presence_eclairage: "Présence d'un éclairage nocturne",
    type_centre: "Type de centre de santé",
    capacite_lits: "Capacité de lits",
    personnel_medical_count: "Nombre de personnels soignants",
    type_pompe: "Type de pompe",
    profondeur: "Profondeur (m)",
    debit: "Débit (m³/h)",
    population_desservie: "Population desservie",
    mode_gestion: "Mode de gestion",
    nombre_boutiques: "Nombre de boutiques",
    superficie: "Superficie (m²)",
    frequence_marche: "Fréquence du marché",
    type_administration: "Type d'administration",
    nombre_bureaux: "Nombre de bureaux",
    type_ouvrage: "Type d'ouvrage",
    longueur_reseau: "Longueur du réseau (m)",
    dimension_capacite: "Dimension / Capacité",
    nature_reseau: "Nature du réseau",
    nature_sport: "Nature de l'infrastructure sportive",
    nature_revetement: "Revêtement",
    capacite_places: "Capacité de places (Gradins)",
    nombre_classes: "Nombre de classes",
    nombre_eleves: "Nombre d'élèves",
    nombre_enseignants: "Nombre d'enseignants",
    cycle_enseignement: "Cycle d'enseignement",
    nom_directeur: "Nom du directeur"
};

const detailFieldIcons = {
    type_technologie: 'fa-bolt',
    nombre_foyers: 'fa-house',
    puissance_lampe: 'fa-bolt',
    hauteur_poteau: 'fa-ruler-vertical',
    presence_cantine: 'fa-utensils',
    presence_maternite: 'fa-baby-carriage',
    ambulance_fonctionnelle: 'fa-ambulance',
    cloture: 'fa-shield-halved',
    salle_reunion: 'fa-users-line',
    accessible_public: 'fa-wheelchair',
    presence_eclairage: 'fa-lightbulb',
    type_centre: 'fa-hospital',
    capacite_lits: 'fa-bed',
    personnel_medical_count: 'fa-user-doctor',
    type_pompe: 'fa-faucet',
    profondeur: 'fa-ruler-vertical',
    debit: 'fa-water',
    population_desservie: 'fa-users',
    mode_gestion: 'fa-cogs',
    nombre_boutiques: 'fa-shop',
    superficie: 'fa-ruler-combined',
    frequence_marche: 'fa-calendar-day',
    type_administration: 'fa-building-flag',
    nombre_bureaux: 'fa-briefcase',
    type_ouvrage: 'fa-gears',
    longueur_reseau: 'fa-ruler',
    dimension_capacite: 'fa-layer-group',
    nature_reseau: 'fa-stream',
    nature_sport: 'fa-futbol',
    nature_revetement: 'fa-border-all',
    capacite_places: 'fa-chair',
    nombre_classes: 'fa-chalkboard',
    nombre_eleves: 'fa-user-graduate',
    nombre_enseignants: 'fa-chalkboard-user',
    cycle_enseignement: 'fa-school',
    nom_directeur: 'fa-user-tie'
};

function getDetailLabel(key) {
    return detailFieldLabels[key] || key.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
}

function getDetailIcon(key) {
    return detailFieldIcons[key] || 'fa-circle-info';
}

function updateDashboardCounters(filteredFeatures) {
    let total = filteredFeatures.length, op = 0, pn = 0, mt = 0;
    filteredFeatures.forEach(f => {
        let st = (f.properties.statut || "").toLowerCase();
        if (st.includes("opérationnel") || st.includes("bon") || st.includes("marche")) op++;
        else if (st.includes("panne") || st.includes("arrêt") || st.includes("mauvais")) pn++;
        else mt++;
    });
    document.getElementById('dash-total').innerText = total;
    document.getElementById('dash-operationnel').innerText = op;
    document.getElementById('dash-panne').innerText = pn;
    document.getElementById('dash-maintenance').innerText = mt;
}

// 3. Popup Commune Professionnelle
fetch('/api/commune/')
    .then(response => response.json())
    .then(data => {
        let geojson = L.geoJSON(data, {
            style: {
                color: "#2980b9",
                weight: 3,
                dashArray: "5, 5",
                fillOpacity: 0
            },
            onEachFeature: function (feature, layer) {
                let props = feature.properties;
                if (props) {
                    let popupContent = `
                        <div class="popup-card" style="font-family: 'Poppins', sans-serif; width: 100%; box-shadow: 0 8px 24px rgba(0,0,0,0.08); border-radius: 12px; overflow: hidden; border: 1px solid #f0f0f0;">
                            <div style="background: linear-gradient(135deg, #2980b9 0%, rgba(0,0,0,0.04) 100%); background-color: #2980b9; color: white; padding: 14px 16px;">
                                <div style="font-size: 10px; text-transform: uppercase; letter-spacing: 0.8px; opacity: 0.85; font-weight: 500; margin-bottom: 2px;">
                                    <i class="fa-solid fa-map me-1"></i> Limite Administrative
                                </div>
                                <div style="font-size: 15px; font-weight: 600; line-height: 1.3;">
                                    ${props.nom || "Territoire Communal"}
                                </div>
                            </div>
                            
                            <div style="padding: 16px; background: white;">
                                <table style="width: 100%; border-collapse: collapse; font-size: 12.5px; color: #4a5568;">
                                    <tr style="border-bottom: 1px dashed #edf2f7;">
                                        <td style="padding: 7px 0; color: #718096; width: 45%;"><i class="fa-solid fa-users me-1"></i> Population :</td>
                                        <td class="text-end fw-semibold" style="padding: 7px 0; color: #2d3748;">${props.population ? props.population.toLocaleString() + ' hab.' : 'N/A'}</td>
                                    </tr>
                                    <tr>
                                        <td style="padding-top: 10px; color: #718096; border: none;"><i class="fa-solid fa-chart-area me-1"></i> Superficie :</td>
                                        <td class="text-end fw-semibold" style="padding-top: 10px; color: #2d3748; border: none;">${props.superficie ? props.superficie + ' km²' : 'N/A'}</td>
                                    </tr>
                                </table>
                            </div>
                        </div>
                    `;
                    layer.bindPopup(popupContent, { maxWidth: 260, minWidth: 260 });
                }
            }
        });
        communeLayer.addLayer(geojson);
    });

// 4. Popup Secteurs Professionnelle
fetch('/api/secteurs/')
    .then(response => response.json())
    .then(data => {
        let geojson = L.geoJSON(data, {
            style: {
                color: "#2ecc71",
                weight: 1.5,
                fillColor: "#2ecc71",
                fillOpacity: 0.05
            },
            onEachFeature: function (feature, layer) {
                let props = feature.properties;
                if (props) {
                   let popupContent = `
                        <div class="popup-card" style="font-family: 'Poppins', sans-serif; width: 100%; box-shadow: 0 8px 24px rgba(0,0,0,0.08); border-radius: 12px; overflow: hidden; border: 1px solid #f0f0f0;">
                            <div style="background: linear-gradient(135deg, #2ecc71 0%, rgba(0,0,0,0.04) 100%); background-color: #2ecc71; color: white; padding: 14px 16px;">
                                <div style="font-size: 10px; text-transform: uppercase; letter-spacing: 0.8px; opacity: 0.85; font-weight: 500; margin-bottom: 2px;">
                                    <i class="fa-solid fa-square-poll-vertical me-1"></i> Découpage Territorial
                                </div>
                                <div style="font-size: 15px; font-weight: 600; line-height: 1.3;">
                                    ${props.nom || "Secteur"}
                                </div>
                            </div>
                            
                            <div style="padding: 16px; background: white;">
                                <table style="width: 100%; border-collapse: collapse; font-size: 12.5px; color: #4a5568;">
                                    <tr style="border-bottom: 1px dashed #edf2f7;">
                                        <td style="padding: 7px 0; color: #718096; width: 45%;"><i class="fa-solid fa-city me-1"></i> Commune :</td>
                                        <td class="text-end fw-semibold" style="padding: 7px 0; color: #2d3748;">${props.commune || "N/A"}</td>
                                    </tr>
                                    <tr>
                                        <td style="padding-top: 10px; color: #718096; border: none;"><i class="fa-solid fa-chart-area me-1"></i> Superficie :</td>
                                        <td class="text-end fw-semibold" style="padding-top: 10px; color: #2d3748; border: none;">${props.superficie ? props.superficie + ' km²' : 'N/A'}</td>
                                    </tr>
                                </table>
                            </div>
                        </div>
                    `;
                    layer.bindPopup(popupContent, { maxWidth: 260, minWidth: 260 });
                }

                layer.on({
                    mouseover: function (e) {
                        e.target.setStyle({ fillOpacity: 0.2, weight: 3 });
                    },
                    mouseout: function (e) {
                        e.target.setStyle({ fillOpacity: 0.05, weight: 1.5 });
                    }
                });
            }
        });
        secteursLayer.addLayer(geojson);
    });

function populateFilterMenus(data) {
    const typesSet = new Set(), statutsSet = new Set(), secteursSet = new Set();
    data.features.forEach(f => {
        if (f.properties) {
            if (f.properties.type_equipement) typesSet.add(f.properties.type_equipement);
            if (f.properties.statut) statutsSet.add(f.properties.statut);
            if (f.properties.secteur) secteursSet.add(String(f.properties.secteur).trim());
        }
    });
    const selectType = document.getElementById('select-type');
    const selectStatut = document.getElementById('select-statut');
    const selectSecteur = document.getElementById('select-secteur');

    typesSet.forEach(t => selectType.add(new Option(t, t)));
    statutsSet.forEach(s => selectStatut.add(new Option(s, s)));
    Array.from(secteursSet).sort().forEach(s => {
        let label = s.toLowerCase().includes('secteur') ? s : "Secteur " + s;
        selectSecteur.add(new Option(label, s));
    });
}

// 6. Application des Filtres + Popup Équipement Professionnelle avec ANNEE
function applyFilters() {
    if (!allEquipementsData) return;

    const searchInputText = document.getElementById('search-equipement').value.toLowerCase().trim();
    const selectedType = document.getElementById('select-type').value;
    const selectedSecteur = document.getElementById('select-secteur').value;
    const selectedStatut = document.getElementById('select-statut').value;

    equipementsLayer.clearLayers();

    const filteredFeatures = allEquipementsData.features.filter(f => {
        let props = f.properties || {};
        let matchesSearch = searchInputText === "" || (props.nom || "").toLowerCase().includes(searchInputText) || (props.code_identification || "").toLowerCase().includes(searchInputText);
        let matchesType = selectedType === "tous" || props.type_equipement === selectedType;
        let matchesSecteur = selectedSecteur === "tous" || String(props.secteur).trim() === selectedSecteur;
        let matchesStatut = selectedStatut === "tous" || props.statut === selectedStatut;
        return matchesSearch && matchesType && matchesSecteur && matchesStatut;
    });

    updateDashboardCounters(filteredFeatures);

    const geojson = L.geoJSON({ type: "FeatureCollection", features: filteredFeatures }, {
    pointToLayer: (feature, latlng) => L.marker(latlng, { icon: getIconForEquipement(feature.properties.type_equipement, feature.properties) }),
        onEachFeature: (feature, layer) => {
            if (feature.properties) {
                let props = feature.properties;
                let style = getStyleByType(props.type_equipement, props);
                let popupContent = `
                    <div class="popup-card" style="font-family: 'Poppins', sans-serif; width: 100%; box-shadow: 0 8px 24px rgba(0,0,0,0.08); border-radius: 12px; overflow: hidden; border: 1px solid #f0f0f0;">
                        <div style="background: linear-gradient(135deg, ${style.color} 0%, rgba(0,0,0,0.04) 100%); background-color: ${style.color}; color: white; padding: 14px 16px;">
                            <div style="font-size: 10px; text-transform: uppercase; letter-spacing: 0.8px; opacity: 0.85; font-weight: 500; margin-bottom: 2px;">
                                <i class="fa-solid ${style.icon} me-1"></i> ${props.type_equipement || "Infrastructure"}
                            </div>
                            <div style="font-size: 15px; font-weight: 600; line-height: 1.3;">
                                ${props.nom || "Sans nom"}
                            </div>
                        </div>
                        
                        <div style="padding: 16px; background: white;">
                            <table style="width: 100%; border-collapse: collapse; font-size: 12.5px; color: #4a5568;">
                                <tr style="border-bottom: 1px dashed #edf2f7;">
                                    <td style="padding: 7px 0; color: #718096; width: 45%;"><i class="fa-solid fa-city me-1"></i> Commune :</td>
                                    <td class="text-end fw-semibold" style="padding: 7px 0; color: #2d3748;">${props.commune}</td>
                                </tr>
                                <tr style="border-bottom: 1px dashed #edf2f7;">
                                    <td style="padding: 7px 0; color: #718096;"><i class="fa-solid fa-location-dot me-1"></i> Localisation :</td>
                                    <td class="text-end fw-semibold" style="padding: 7px 0; color: #2d3748;">${props.secteur}</td>
                                </tr>
                                <tr style="border-bottom: 1px dashed #edf2f7;">
                                    <td style="padding: 7px 0; color: #718096;"><i class="fa-solid fa-calendar me-1"></i> Réalisation :</td>
                                    <td class="text-end fw-semibold" style="padding: 7px 0; color: #2d3748;">${props.annee_realisation}</td>
                                </tr>
                                <tr style="border-bottom: 1px dashed #edf2f7;">
                                    <td style="padding: 7px 0; color: #718096;"><i class="fa-solid fa-layer-group me-1"></i> État Physique :</td>
                                    <td class="text-end fw-semibold" style="padding: 7px 0; color: #2d3748;">${props.etat || "Non spécifié"}</td>
                                </tr>
                                        <tr>
                                            <td style="padding-top: 10px; color: #718096; font-weight: bold; border: none;"><i class="fa-solid fa-circle-info me-1"></i> Fonctionnement :</td>
                                            <td class="text-end" style="padding-top: 10px; border: none;">${getStatusBadge(props.statut)}</td>
                                        </tr>
                                        ${(() => {
                                            let dhtml = '';
                                            if (props.details) {
                                                for (const [k,v] of Object.entries(props.details)) {
                                                    // Format boolean values as Oui/Non
                                                    let display = v;
                                                    if (typeof v === 'boolean') display = v ? 'Oui' : 'Non';
                                                    if (v === null || v === undefined || v === '') display = 'N/A';
                                                    dhtml += `<tr style="border-bottom: 1px dashed #edf2f7;"><td style="padding: 7px 0; color: #718096; text-transform: capitalize;">${k.replace(/_/g,' ')} :</td><td class="text-end fw-semibold" style="padding: 7px 0; color: #2d3748;">${display}</td></tr>`;
                                                }
                                            }
                                            return dhtml;
                                        })()}
                            </table>
                        </div>
                    </div>
                `;
                layer.bindPopup(popupContent, { maxWidth: 300, minWidth: 300 });
            }
        }
    });
    equipementsLayer.addLayer(geojson);
}

fetch('/api/equipements/')
    .then(response => response.json())
    .then(data => {
        allEquipementsData = data;
        populateFilterMenus(data);
        applyFilters();
    });

// Écouteurs de changements
document.getElementById('search-equipement').addEventListener('input', applyFilters);
document.getElementById('select-type').addEventListener('change', applyFilters);
document.getElementById('select-secteur').addEventListener('change', applyFilters);
document.getElementById('select-statut').addEventListener('change', applyFilters);

// 7. ACTION DU BOUTON DE REINITIALISATION AUTOMATIQUE
document.getElementById('btn-reset').addEventListener('click', function() {
    document.getElementById('search-equipement').value = "";
    document.getElementById('select-type').value = "tous";
    document.getElementById('select-secteur').value = "tous";
    document.getElementById('select-statut').value = "tous";
    applyFilters();
});