// ------------------------------------------------------------------
// FitFuel — progress charts (weight line + weekly workouts bars)
// ------------------------------------------------------------------
document.addEventListener('DOMContentLoaded', function () {
    var dataEl = document.getElementById('progress-data');
    if (!dataEl || typeof Chart === 'undefined') return;

    var d;
    try { d = JSON.parse(dataEl.textContent); } catch (e) { return; }

    var ACCENT = '#ff6b35';
    var TEXT = '#b6b6c2';
    var GRID = 'rgba(255, 255, 255, 0.08)';

    Chart.defaults.color = TEXT;
    Chart.defaults.font.family = "'Poppins', sans-serif";
    Chart.defaults.borderColor = GRID;

    var weightCanvas = document.getElementById('weightChart');
    if (weightCanvas && d.weight_values.length) {
        var min = Math.min.apply(null, d.weight_values);
        var max = Math.max.apply(null, d.weight_values);
        new Chart(weightCanvas, {
            type: 'line',
            data: {
                labels: d.weight_labels,
                datasets: [{
                    label: 'Weight (kg)',
                    data: d.weight_values,
                    borderColor: ACCENT,
                    backgroundColor: 'rgba(255, 107, 53, 0.15)',
                    pointBackgroundColor: ACCENT,
                    pointRadius: 4,
                    tension: 0.3,
                    fill: true
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { display: false } },
                scales: {
                    y: { suggestedMin: Math.floor(min - 1), suggestedMax: Math.ceil(max + 1), title: { display: true, text: 'kg' } },
                    x: { grid: { display: false } }
                }
            }
        });
    }

    var workoutCanvas = document.getElementById('workoutChart');
    if (workoutCanvas && d.workout_values.length) {
        var goalLine = d.workout_values.map(function () { return d.workout_target; });
        new Chart(workoutCanvas, {
            data: {
                labels: d.weight_labels,
                datasets: [
                    {
                        type: 'bar',
                        label: 'Workouts',
                        data: d.workout_values,
                        backgroundColor: d.workout_values.map(function (v) {
                            return v >= d.workout_target ? ACCENT : 'rgba(255, 107, 53, 0.4)';
                        }),
                        borderRadius: 6
                    },
                    {
                        type: 'line',
                        label: 'Goal (' + d.workout_target + ')',
                        data: goalLine,
                        borderColor: '#f5f1ea',
                        borderDash: [6, 6],
                        borderWidth: 1.5,
                        pointRadius: 0,
                        fill: false
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { labels: { boxWidth: 12 } } },
                scales: {
                    y: { beginAtZero: true, suggestedMax: 7, ticks: { stepSize: 1 } },
                    x: { grid: { display: false } }
                }
            }
        });
    }
});
