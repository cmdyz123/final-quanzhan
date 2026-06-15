/**
 * Dashboard chart initialization
 */

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
