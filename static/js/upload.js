/**
 * Food image upload + manual input handling
 */

document.addEventListener('DOMContentLoaded', function() {
    // === Photo Upload ===
    const dropZone = document.getElementById('dropZone');
    const fileInput = document.getElementById('food_image');
    const preview = document.getElementById('preview');
    const uploadForm = document.getElementById('uploadForm');
    const submitBtn = document.getElementById('submitPhotoBtn');

    if (dropZone && fileInput) {
        dropZone.addEventListener('click', function(e) {
            if (e.target.tagName !== 'IMG') {
                fileInput.click();
            }
        });

        fileInput.addEventListener('change', function() {
            handleFile(fileInput.files[0]);
        });

        dropZone.addEventListener('dragover', function(e) {
            e.preventDefault();
            dropZone.classList.add('drag-over');
        });

        dropZone.addEventListener('dragleave', function() {
            dropZone.classList.remove('drag-over');
        });

        dropZone.addEventListener('drop', function(e) {
            e.preventDefault();
            dropZone.classList.remove('drag-over');
            const file = e.dataTransfer.files[0];
            if (file) {
                fileInput.files = e.dataTransfer.files;
                handleFile(file);
            }
        });

        function handleFile(file) {
            if (!file) return;
            const allowedTypes = ['image/jpeg', 'image/png', 'image/gif', 'image/webp'];
            if (!allowedTypes.includes(file.type)) {
                alert('仅支持 JPG、PNG、GIF、WebP 格式的图片');
                return;
            }
            if (file.size > 16 * 1024 * 1024) {
                alert('图片大小不能超过16MB');
                return;
            }
            const reader = new FileReader();
            reader.onload = function(e) {
                preview.src = e.target.result;
                preview.classList.remove('d-none');
                const placeholders = dropZone.querySelectorAll('.bi-cloud-arrow-up, p');
                placeholders.forEach(function(el) { el.style.display = 'none'; });
            };
            reader.readAsDataURL(file);
        }

        if (uploadForm) {
            uploadForm.addEventListener('submit', function() {
                if (submitBtn && !submitBtn.disabled) {
                    submitBtn.disabled = true;
                    submitBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span> AI正在分析中...';
                }
            });
        }
    }

    // === Manual Input ===
    const allFoodsEl = document.getElementById('allFoodsData');
    let allFoods = [];
    if (allFoodsEl) {
        try {
            allFoods = JSON.parse(allFoodsEl.textContent);
        } catch(e) {
            allFoods = [];
        }
    }

    const foodRows = document.getElementById('foodRows');
    const addFoodRowBtn = document.getElementById('addFoodRow');

    // Add food row
    if (addFoodRowBtn && foodRows) {
        addFoodRowBtn.addEventListener('click', function() {
            addFoodRow();
        });
    }

    // Delegate events for remove buttons and search inputs
    if (foodRows) {
        foodRows.addEventListener('click', function(e) {
            if (e.target.closest('.remove-food-row')) {
                const row = e.target.closest('.food-row');
                const allRows = foodRows.querySelectorAll('.food-row');
                if (allRows.length > 1) {
                    row.remove();
                } else {
                    // Clear the only row
                    row.querySelector('.food-search').value = '';
                    row.querySelector('input[name="food_portion[]"]').value = '100';
                }
            }
        });

        foodRows.addEventListener('input', function(e) {
            if (e.target.classList.contains('food-search')) {
                handleFoodSearch(e.target);
            }
        });

        // Hide suggestions when clicking outside
        document.addEventListener('click', function(e) {
            if (!e.target.closest('.food-search')) {
                document.querySelectorAll('.food-suggestions').forEach(function(el) {
                    el.classList.add('d-none');
                });
            }
        });
    }

    function addFoodRow() {
        if (!foodRows) return;
        const row = document.createElement('div');
        row.className = 'food-row row g-2 mb-2';
        row.innerHTML = `
            <div class="col-6 position-relative">
                <input type="text" class="form-control food-search" name="food_name[]"
                       placeholder="输入食物名称" autocomplete="off" required>
                <div class="food-suggestions list-group position-absolute d-none" style="z-index:1000; max-height:200px; overflow-y:auto;"></div>
            </div>
            <div class="col-3">
                <input type="number" class="form-control" name="food_portion[]"
                       placeholder="分量(g)" value="100" min="10" max="2000">
            </div>
            <div class="col-2">
                <button type="button" class="btn btn-outline-danger btn-sm remove-food-row" title="删除">
                    <i class="bi bi-x-lg"></i>
                </button>
            </div>
        `;
        foodRows.appendChild(row);
    }

    function handleFoodSearch(input) {
        const keyword = input.value.trim();
        const suggestionEl = input.parentElement.querySelector('.food-suggestions');
        if (!suggestionEl) return;

        if (keyword.length < 1) {
            suggestionEl.classList.add('d-none');
            return;
        }

        // Fuzzy filter local food list
        const kw = keyword.toLowerCase();
        const matches = allFoods.filter(function(name) {
            return name.toLowerCase().includes(kw) || kw.split('').some(function(c) { return name.includes(c); });
        }).slice(0, 8);

        if (matches.length === 0) {
            // Also search via API
            fetch('/api/search-food?q=' + encodeURIComponent(keyword))
                .then(function(r) { return r.json(); })
                .then(function(data) {
                    showSuggestions(input, suggestionEl, data.results.map(function(r) { return r.name; }));
                });
        } else {
            showSuggestions(input, suggestionEl, matches);
        }
    }

    function showSuggestions(input, suggestionEl, items) {
        if (items.length === 0) {
            suggestionEl.classList.add('d-none');
            return;
        }

        suggestionEl.innerHTML = items.map(function(name) {
            return '<button type="button" class="list-group-item list-group-item-action py-1 px-2 small">'
                + name + '</button>';
        }).join('');

        suggestionEl.classList.remove('d-none');

        // Click handler
        suggestionEl.querySelectorAll('button').forEach(function(btn) {
            btn.addEventListener('click', function() {
                input.value = btn.textContent.trim();
                suggestionEl.classList.add('d-none');
            });
        });
    }

    // === Tab sync for meal_type ===
    const mealTypePhoto = document.getElementById('meal_type_photo');
    const mealTypeManual = document.getElementById('meal_type_manual');

    if (mealTypePhoto && mealTypeManual) {
        mealTypePhoto.addEventListener('change', function() {
            mealTypeManual.value = mealTypePhoto.value;
        });
        mealTypeManual.addEventListener('change', function() {
            mealTypePhoto.value = mealTypeManual.value;
        });
    }

    // === Load manual submit ===
    const manualForm = document.getElementById('manualForm');
    const submitManualBtn = document.getElementById('submitManualBtn');
    if (manualForm && submitManualBtn) {
        manualForm.addEventListener('submit', function() {
            submitManualBtn.disabled = true;
            submitManualBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span> 正在保存...';
        });
    }

    // === Quick Text Record ===
    const quickInput = document.getElementById('quickFoodInput');
    const quickBtn = document.getElementById('quickRecordBtn');
    const quickResult = document.getElementById('quickResult');

    if (quickInput && quickBtn) {
        // Enter key submit
        quickInput.addEventListener('keydown', function(e) {
            if (e.key === 'Enter') {
                e.preventDefault();
                quickBtn.click();
            }
        });

        quickBtn.addEventListener('click', function() {
            const text = quickInput.value.trim();
            if (!text) {
                alert('请输入食物名称');
                return;
            }

            const mealType = document.getElementById('meal_type_manual')
                ? document.getElementById('meal_type_manual').value
                : 'lunch';
            const priceInput = document.getElementById('price_manual');
            const price = priceInput ? parseFloat(priceInput.value) || null : null;
            const notesInput = document.getElementById('notes_manual');
            const notes = notesInput ? notesInput.value.trim() : '';

            // Disable button
            quickBtn.disabled = true;
            quickBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span> 识别中...';

            // Show loading in result area
            if (quickResult) {
                quickResult.classList.remove('d-none', 'alert-danger', 'alert-success');
                quickResult.classList.add('alert', 'alert-info');
                quickResult.innerHTML = '... AI ' + text + ' ...';
            }

            fetch('/api/quick-record', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    text: text,
                    meal_type: mealType,
                    price: price,
                    notes: notes
                })
            })
            .then(function(r) { return r.json(); })
            .then(function(data) {
                quickBtn.disabled = false;
                quickBtn.innerHTML = '<i class="bi bi-lightning"></i> 识别记录';

                if (data.success) {
                    var foods = data.foods.map(function(f) {
                        return f.name + '(' + f.portion_g + 'g)';
                    }).join(' + ');

                    if (quickResult) {
                        quickResult.classList.remove('alert-info', 'alert-danger');
                        quickResult.classList.add('alert-success');
                        quickResult.innerHTML = '<strong>' + foods + '</strong><br>' +
                            '热量: ' + data.nutrition.calories + '千卡 | ' +
                            '蛋白质: ' + data.nutrition.protein + 'g | ' +
                            '脂肪: ' + data.nutrition.fat + 'g | ' +
                            '碳水: ' + data.nutrition.carbs + 'g<br>' +
                            '<small class="text-muted">' + data.analysis + '</small><br>' +
                            '<a href="/dashboard" class="btn btn-sm btn-primary mt-2">查看仪表盘</a>';
                    }

                    quickInput.value = '';

                    // Auto switch to right panel refresh - just scroll to top
                    window.scrollTo({ top: 0, behavior: 'smooth' });
                } else {
                    if (quickResult) {
                        quickResult.classList.remove('alert-info');
                        quickResult.classList.add('alert-danger');
                        quickResult.innerHTML = data.error || '';
                    }
                }
            })
            .catch(function(err) {
                quickBtn.disabled = false;
                quickBtn.innerHTML = '<i class="bi bi-lightning"></i> 识别记录';
                if (quickResult) {
                    quickResult.classList.remove('alert-info');
                    quickResult.classList.add('alert-danger');
                    quickResult.innerHTML = ': ' + err.message;
                }
            });
        });
    }
});
