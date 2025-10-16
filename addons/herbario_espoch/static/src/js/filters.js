/* ==================== HERBARIO ESPOCH - FILTROS DINÁMICOS ==================== */

(function() {
    'use strict';

    document.addEventListener('DOMContentLoaded', function() {
        
        // ==================== AUTO-SUBMIT DE FILTROS ====================
        const filterForm = document.getElementById('herbario-filter-form');
        if (filterForm) {
            const selects = filterForm.querySelectorAll('select');
            selects.forEach(select => {
                select.addEventListener('change', function() {
                    filterForm.submit();
                });
            });
        }

        // ==================== BÚSQUEDA CON AUTOCOMPLETADO ====================
        const searchInput = document.getElementById('herbario-search-input');
        if (searchInput) {
            let searchTimeout;
            
            searchInput.addEventListener('input', function() {
                clearTimeout(searchTimeout);
                const query = this.value.trim();
                
                if (query.length < 3) {
                    hideAutocomplete();
                    return;
                }
                
                searchTimeout = setTimeout(function() {
                    performSearch(query);
                }, 300);
            });
            
            // Ocultar al hacer clic fuera
            document.addEventListener('click', function(e) {
                if (!searchInput.contains(e.target)) {
                    hideAutocomplete();
                }
            });
        }

        function performSearch(query) {
            fetch('/herbario/api/search', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    jsonrpc: '2.0',
                    method: 'call',
                    params: {
                        query: query,
                        limit: 10
                    }
                })
            })
            .then(response => response.json())
            .then(data => {
                if (data.result && data.result.length > 0) {
                    showAutocomplete(data.result);
                } else {
                    hideAutocomplete();
                }
            })
            .catch(error => {
                console.error('Error en búsqueda:', error);
            });
        }

        function showAutocomplete(results) {
            let autocompleteDiv = document.getElementById('herbario-autocomplete');
            if (!autocompleteDiv) {
                autocompleteDiv = document.createElement('div');
                autocompleteDiv.id = 'herbario-autocomplete';
                autocompleteDiv.className = 'herbario-autocomplete';
                searchInput.parentNode.appendChild(autocompleteDiv);
            }
            
            let html = '<ul class="herbario-autocomplete-list">';
            results.forEach(item => {
                html += `
                    <li class="herbario-autocomplete-item" data-url="${item.url}">
                        <div class="herbario-autocomplete-name">${item.nombre_cientifico}</div>
                        <div class="herbario-autocomplete-meta">
                            <span class="herbario-autocomplete-familia">${item.familia}</span>
                            <span class="herbario-autocomplete-codigo">${item.codigo}</span>
                        </div>
                    </li>
                `;
            });
            html += '</ul>';
            
            autocompleteDiv.innerHTML = html;
            autocompleteDiv.style.display = 'block';
            
            // Agregar event listeners a los items
            const items = autocompleteDiv.querySelectorAll('.herbario-autocomplete-item');
            items.forEach(item => {
                item.addEventListener('click', function() {
                    window.location.href = this.dataset.url;
                });
            });
        }

        function hideAutocomplete() {
            const autocompleteDiv = document.getElementById('herbario-autocomplete');
            if (autocompleteDiv) {
                autocompleteDiv.style.display = 'none';
            }
        }

        // ==================== LIMPIAR FILTROS ====================
        const clearFiltersBtn = document.getElementById('herbario-clear-filters');
        if (clearFiltersBtn) {
            clearFiltersBtn.addEventListener('click', function(e) {
                e.preventDefault();
                const form = document.getElementById('herbario-filter-form');
                if (form) {
                    // Limpiar todos los selects
                    form.querySelectorAll('select').forEach(select => {
                        select.selectedIndex = 0;
                    });
                    // Limpiar inputs
                    form.querySelectorAll('input[type="text"], input[type="search"]').forEach(input => {
                        input.value = '';
                    });
                    // Remover parámetros de la URL
                    window.location.href = window.location.pathname;
                }
            });
        }

        // ==================== CONTADOR DE FILTROS ACTIVOS ====================
        function updateFilterCount() {
            const form = document.getElementById('herbario-filter-form');
            if (!form) return;
            
            let activeCount = 0;
            
            form.querySelectorAll('select').forEach(select => {
                if (select.value && select.value !== '') {
                    activeCount++;
                }
            });
            
            form.querySelectorAll('input[type="text"], input[type="search"]').forEach(input => {
                if (input.value && input.value.trim() !== '') {
                    activeCount++;
                }
            });
            
            const countBadge = document.getElementById('herbario-filter-count');
            if (countBadge) {
                countBadge.textContent = activeCount;
                countBadge.style.display = activeCount > 0 ? 'inline-block' : 'none';
            }
        }
        
        updateFilterCount();

        // ==================== TOGGLE FILTROS EN MOBILE ====================
        const filterToggle = document.getElementById('herbario-filter-toggle');
        const filterPanel = document.querySelector('.herbario-filters');
        
        if (filterToggle && filterPanel) {
            filterToggle.addEventListener('click', function() {
                filterPanel.classList.toggle('herbario-filters-visible');
            });
        }

    });

})();

/* ==================== ESTILOS CSS PARA AUTOCOMPLETADO ==================== */
const style = document.createElement('style');
style.textContent = `
    .herbario-autocomplete {
        position: absolute;
        top: 100%;
        left: 0;
        right: 0;
        background: white;
        border: 1px solid #ddd;
        border-top: none;
        border-radius: 0 0 5px 5px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        z-index: 1000;
        max-height: 400px;
        overflow-y: auto;
    }
    
    .herbario-autocomplete-list {
        list-style: none;
        margin: 0;
        padding: 0;
    }
    
    .herbario-autocomplete-item {
        padding: 12px 15px;
        cursor: pointer;
        border-bottom: 1px solid #f0f0f0;
        transition: background 0.2s ease;
    }
    
    .herbario-autocomplete-item:hover {
        background: #f8f9fa;
    }
    
    .herbario-autocomplete-name {
        font-weight: 600;
        font-style: italic;
        color: #2d5f3f;
        margin-bottom: 4px;
    }
    
    .herbario-autocomplete-meta {
        font-size: 0.85rem;
        color: #666;
        display: flex;
        justify-content: space-between;
    }
    
    .herbario-autocomplete-familia {
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    
    .herbario-autocomplete-codigo {
        font-weight: 600;
        color: #999;
    }
    
    @media (max-width: 768px) {
        .herbario-filters {
            display: none;
        }
        
        .herbario-filters-visible {
            display: block !important;
        }
    }
`;
document.head.appendChild(style);