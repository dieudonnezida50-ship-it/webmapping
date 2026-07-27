document.addEventListener("DOMContentLoaded", function() {
    
    // ==========================================================================
    // 1. GESTION DES GRAPHIQUES (Sécurisée pour éviter les crashs)
    // ==========================================================================
    const chartCanvas = document.getElementById('statutChart');
    
    // On n'exécute le code du graphique QUE si l'élément existe sur la page
    if (chartCanvas) {
        const ctx = chartCanvas.getContext('2d');
        
        // Sécurité pour les variables : on vérifie si elles existent, sinon on met 0
        let op = 0;
        let maint = 0;
        let pn = 0;

        if (typeof statsData !== 'undefined') {
            op = statsData.operationnels || 0;
            maint = statsData.maintenance || 0;
            pn = statsData.panne || 0;
        } else if (typeof totalEquipements !== 'undefined' && typeof enPanneEquipements !== 'undefined') {
            op = totalEquipements - enPanneEquipements;
            pn = enPanneEquipements;
        }

        // Initialisation unique du graphique Chart.js
        new Chart(ctx, {
            type: 'doughnut', 
            data: {
                labels: ['Opérationnels', 'En Maintenance', 'En Panne'],
                datasets: [{
                    data: [op, maint, pn],
                    backgroundColor: [
                        '#2ecc71', // Vert succès
                        '#f1c40f', // Jaune maintenance
                        '#e74c3c'  // Rouge panne
                    ],
                    borderWidth: 2,
                    borderColor: '#ffffff',
                    hoverOffset: 4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false, 
                cutout: '70%', 
                plugins: {
                    legend: {
                        position: 'bottom',
                        labels: {
                            usePointStyle: true,
                            padding: 20,
                            font: {
                                family: "'Poppins', sans-serif",
                                size: 12
                            }
                        }
                    }
                }
            }
        });
    }

    // ==========================================================================
    // 2. ANIMATION DES COMPTEURS NUMÉRIQUES DES CARTES (COUNTER-UP)
    // ==========================================================================
    const counters = document.querySelectorAll('.card-number');
    
    counters.forEach(counter => {
        const target = parseInt(counter.innerText, 10);
        if (target === 0 || isNaN(target)) return;

        const duration = 1200; 
        const stepTime = Math.max(Math.floor(duration / target), 15);
        let current = 0;

        const timer = setInterval(() => {
            current += Math.ceil(target / (duration / stepTime));
            if (current >= target) {
                counter.innerText = target;
                clearInterval(timer);
            } else {
                counter.innerText = current;
            }
        }, stepTime);
    });

    // ==========================================================================
    // 3. GESTION DE LA CLASSE ACTIVE DANS LA SIDEBAR
    // ==========================================================================
    const menuLinks = document.querySelectorAll('.sidebar-menu .nav-link');
    const currentUrl = window.location.pathname;

    menuLinks.forEach(link => {
        if (link.getAttribute('href') === currentUrl) {
            menuLinks.forEach(item => item.classList.remove('active', 'bg-primary', 'bg-gradient', 'text-white'));
            link.classList.add('active', 'bg-primary', 'bg-gradient', 'text-white');
        }
    });
});