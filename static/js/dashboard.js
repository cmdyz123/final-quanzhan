/**
 * Dashboard chart initialization + daily summary
 */

function loadDailySummary() {
    var row = document.getElementById('dailySummaryRow');
    var body = document.getElementById('dailySummaryBody');
    var loading = document.getElementById('summaryLoading');
    var content = document.getElementById('summaryContent');

    if (!row || row.style.display === 'none') return;

    var params = new URLSearchParams(window.location.search);
    var dateParam = params.get('date') || '';
    var url = '/api/daily-summary';
    if (dateParam) url += '?date=' + dateParam;

    fetch(url)
        .then(function(r) { return r.json(); })
        .then(function(data) {
            if (!data.ready) {
                // Not all meals done yet - hide the row
                row.style.display = 'none';
                return;
            }

            // Show the summary
            if (loading) loading.classList.add('d-none');
            if (content) {
                content.classList.remove('d-none');

                var summary = data.summary;
                var foods = summary.all_foods.join('、') || '无记录';

                var html = '';

                // AI summary text
                if (data.ai_summary) {
                    html += '<div class="alert alert-light border mb-3" style="white-space: pre-line; line-height: 1.8;">';
                    html += data.ai_summary;
                    html += '</div>';
                }

                // Quick stats
                html += '<div class="row g-2 text-center small">';
                html += '<div class="col-3"><div class="border rounded p-2"><strong class="text-danger">' + summary.total_cal + '</strong><br>总热量(千卡)</div></div>';
                html += '<div class="col-3"><div class="border rounded p-2"><strong class="text-primary">' + summary.total_protein + '</strong><br>蛋白质(g)</div></div>';
                html += '<div class="col-3"><div class="border rounded p-2"><strong class="text-warning">' + summary.total_fat + '</strong><br>脂肪(g)</div></div>';
                html += '<div class="col-3"><div class="border rounded p-2"><strong class="text-success">' + summary.total_carbs + '</strong><br>碳水(g)</div></div>';
                html += '</div>';

                // Meal status
                var mealLabels = {'breakfast': '早餐', 'lunch': '午餐', 'dinner': '晚餐'};
                html += '<div class="mt-2 small text-muted">';
                for (var mt in summary.meal_status) {
                    var s = summary.meal_status[mt];
                    html += '<span class="me-2">' + mealLabels[mt] + ': ';
                    html += s === 'skipped' ? '⏭️跳过' : '✅已记录';
                    html += '</span>';
                }
                html += '<span class="ms-2">💰 消费: ¥' + summary.total_price + '</span>';
                html += '</div>';

                content.innerHTML = html;
            }
        })
        .catch(function(err) {
            console.error('Daily summary error:', err);
        });
}

function initDashboardCharts(weekData, dailyAnalysis) {
    // Weekly calorie + price chart
    const weekCtx = document.getElementById('weeklyChart');
    if (weekCtx) {
        new Chart(weekCtx, {
            type: 'bar',
            data: {
                labels: weekData.labels,
                datasets: [
                    {
                        label: '热量 (千卡)',
                        data: weekData.calories,
                        backgroundColor: weekData.calories.map(function(v) {
                            if (v > 2500) return '#e74a3b';
                            if (v > 2000) return '#f6c23e';
                            return '#1cc88a';
                        }),
                        borderRadius: 6,
                        borderSkipped: false,
                        yAxisID: 'y'
                    },
                    {
                        label: '消费 (元)',
                        data: weekData.price || [],
                        type: 'line',
                        borderColor: '#36b9cc',
                        backgroundColor: 'rgba(54, 185, 204, 0.1)',
                        fill: true,
                        tension: 0.4,
                        pointRadius: 4,
                        pointBackgroundColor: '#36b9cc',
                        yAxisID: 'y1'
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { position: 'bottom' },
                    tooltip: {
                        callbacks: {
                            label: function(ctx) {
                                if (ctx.dataset.label === '热量 (千卡)') {
                                    return '热量: ' + ctx.raw + ' 千卡';
                                }
                                return '消费: \u00a5' + ctx.raw;
                            }
                        }
                    }
                },
                scales: {
                    y: {
                        type: 'linear',
                        position: 'left',
                        beginAtZero: true,
                        title: { display: true, text: '千卡' }
                    },
                    y1: {
                        type: 'linear',
                        position: 'right',
                        beginAtZero: true,
                        title: { display: true, text: '元' },
                        grid: { drawOnChartArea: false }
                    }
                }
            }
        });
    }

    // Macro doughnut chart
    const macroCtx = document.getElementById('macroChart');
    if (macroCtx && dailyAnalysis && dailyAnalysis.totals) {
        const totals = dailyAnalysis.totals;
        new Chart(macroCtx, {
            type: 'doughnut',
            data: {
                labels: ['蛋白质', '脂肪', '碳水化合物', '膳食纤维'],
                datasets: [{
                    data: [
                        Math.max(totals.protein || 0, 0.1),
                        Math.max(totals.fat || 0, 0.1),
                        Math.max(totals.carbs || 0, 0.1),
                        Math.max(totals.fiber || 0, 0.1)
                    ],
                    backgroundColor: ['#4e73df', '#f6c23e', '#1cc88a', '#36b9cc'],
                    borderWidth: 3,
                    borderColor: '#fff'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                cutout: '65%',
                plugins: {
                    legend: {
                        position: 'bottom',
                        labels: { padding: 20, usePointStyle: true }
                    },
                    tooltip: {
                        callbacks: {
                            label: function(ctx) {
                                return ctx.label + ': ' + Math.round(ctx.raw) + 'g';
                            }
                        }
                    }
                }
            }
        });
    }
}
