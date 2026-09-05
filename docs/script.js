document.addEventListener('DOMContentLoaded', () => {

    // ==================== HELPERS ====================

    function getAqiDetails(aqi) {
        if (aqi <= 50) return { label: 'Good', className: 'bg-good' };
        if (aqi <= 100) return { label: 'Moderate', className: 'bg-moderate' };
        if (aqi <= 150) return { label: 'Unhealthy for Sensitive', className: 'bg-sensitive' };
        if (aqi <= 200) return { label: 'Unhealthy', className: 'bg-unhealthy' };
        return { label: 'Hazardous', className: 'bg-hazardous' };
    }

    function formatDate(dateString) {
        const options = { weekday: 'short', month: 'short', day: 'numeric' };
        return new Date(dateString).toLocaleDateString(undefined, options);
    }

    function formatFeatureName(name) {
        return name.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
    }

    // ==================== TAB NAVIGATION ====================

    const tabBtns = document.querySelectorAll('.tab-btn');
    const tabPanels = document.querySelectorAll('.tab-panel');

    tabBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            const target = btn.dataset.tab;

            tabBtns.forEach(b => b.classList.remove('active'));
            tabPanels.forEach(p => p.classList.remove('active'));

            btn.classList.add('active');
            document.getElementById('panel' + target.charAt(0).toUpperCase() + target.slice(1)).classList.add('active');
        });
    });

    // ==================== FETCH DATA ====================

    async function fetchData() {
        try {
            const response = await fetch('predictions.json');
            const result = await response.json();

            if (result.status === 'success') {
                populateDashboard(result.data);
                document.getElementById('loader').classList.add('hidden');
                document.getElementById('dashboard').classList.remove('hidden');
            } else {
                console.error("API Error:", result.message);
                showError("Failed to load predictions.");
            }
        } catch (error) {
            console.error("Network Error:", error);
            showError("Failed to connect to the prediction API.");
        }
    }

    function showError(msg) {
        document.getElementById('loader').innerHTML = `
            <div style="text-align:center; color:#DC2626; padding:3rem;">
                <p style="font-size:1.2rem; font-weight:600;">⚠️ ${msg}</p>
                <p style="color:#64748B; margin-top:0.5rem;">Check console for details.</p>
            </div>`;
    }

    // ==================== POPULATE DASHBOARD ====================

    function populateDashboard(data) {
        populateForecast(data);
        populateModels(data);
        populateShap(data);
    }

    // ==================== TAB 1: FORECAST ====================

    function populateForecast(data) {
        const currentAqi = Math.round(data.current_aqi);
        const currentDetails = getAqiDetails(currentAqi);

        document.getElementById('currentDateLabel').textContent = `As of ${formatDate(data.current_date)}`;
        document.getElementById('currentAqiValue').textContent = currentAqi;
        document.getElementById('currentAqiCategory').textContent = currentDetails.label;
        document.getElementById('currentAqiCategory').className = `aqi-category ${currentDetails.className}`;

        const preds = [
            { id: 'day1', key: '1_day' },
            { id: 'day2', key: '2_days' },
            { id: 'day3', key: '3_days' },
        ];

        preds.forEach(({ id, key }) => {
            const val = Math.round(data.predictions[key]);
            const details = getAqiDetails(val);
            document.getElementById(`${id}Value`).textContent = val;
            document.getElementById(`${id}Category`).textContent = details.label;
            document.getElementById(`${id}Category`).className = `forecast-category ${details.className}`;
        });

        renderHistoryChart(data);
    }

    function renderHistoryChart(data) {
        const ctx = document.getElementById('aqiChart').getContext('2d');

        const historyLabels = data.history.map(item => formatDate(item.date));
        const historyData = data.history.map(item => Math.round(item.aqi));

        const lastDate = new Date(data.current_date);
        const futureLabels = [1, 2, 3].map(d => {
            const dt = new Date(lastDate);
            dt.setDate(dt.getDate() + d);
            return formatDate(dt);
        });

        const allLabels = [...historyLabels, ...futureLabels];
        const histDataPadded = [...historyData, null, null, null];

        const currentAqi = Math.round(data.current_aqi);
        const p1 = Math.round(data.predictions['1_day']);
        const p2 = Math.round(data.predictions['2_days']);
        const p3 = Math.round(data.predictions['3_days']);

        const nulls = new Array(data.history.length - 1).fill(null);
        const predDataPadded = [...nulls, currentAqi, p1, p2, p3];

        new Chart(ctx, {
            type: 'line',
            data: {
                labels: allLabels,
                datasets: [
                    {
                        label: 'Historical AQI',
                        data: histDataPadded,
                        borderColor: '#0284C7',
                        backgroundColor: 'rgba(2, 132, 199, 0.08)',
                        borderWidth: 2.5,
                        pointRadius: 4,
                        pointBackgroundColor: '#0284C7',
                        fill: true,
                        tension: 0.35,
                    },
                    {
                        label: 'Predicted AQI',
                        data: predDataPadded,
                        borderColor: '#0F172A',
                        borderDash: [6, 4],
                        borderWidth: 2.5,
                        pointRadius: 5,
                        pointBackgroundColor: '#0F172A',
                        fill: false,
                        tension: 0.35,
                    },
                ],
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        labels: {
                            color: '#1E293B',
                            font: { family: 'Inter', size: 13, weight: '600' },
                            usePointStyle: true,
                            padding: 20,
                        },
                    },
                    tooltip: {
                        mode: 'index',
                        intersect: false,
                        backgroundColor: '#0F172A',
                        titleFont: { family: 'Inter', size: 13 },
                        bodyFont: { family: 'JetBrains Mono', size: 12 },
                        cornerRadius: 8,
                        padding: 12,
                    },
                },
                scales: {
                    x: {
                        ticks: { color: '#64748B', font: { family: 'Inter', size: 11 } },
                        grid: { color: 'rgba(0,0,0,0.04)' },
                    },
                    y: {
                        beginAtZero: true,
                        ticks: { color: '#64748B', font: { family: 'JetBrains Mono', size: 11 } },
                        grid: { color: 'rgba(0,0,0,0.04)' },
                    },
                },
            },
        });
    }

    // ==================== TAB 2: MODEL DETAILS ====================

    function populateModels(data) {
        const grid = document.getElementById('modelCardsGrid');
        const chipsContainer = document.getElementById('featureChips');

        if (!data.model_info) {
            grid.innerHTML = '<p style="color:#64748B;">Model metadata not yet available. Run the retrain pipeline to generate.</p>';
            return;
        }

        const horizonLabels = {
            '1d': '1-Day Forecast',
            '2d': '2-Day Forecast',
            '3d': '3-Day Forecast',
        };

        grid.innerHTML = '';

        Object.entries(horizonLabels).forEach(([key, label]) => {
            const info = data.model_info[key];
            const metrics = data.evaluation_metrics?.[key];

            if (!info) return;

            const card = document.createElement('div');
            card.className = 'model-card';

            let metricsHTML = '';
            if (metrics) {
                const r2Class = metrics.r2 >= 0.8 ? 'good' : metrics.r2 >= 0.5 ? 'warning' : 'bad';
                metricsHTML = `
                    <div class="metric-row">
                        <span class="metric-label">R² Score</span>
                        <span class="metric-value ${r2Class}">${metrics.r2.toFixed(4)}</span>
                    </div>
                    <div class="metric-row">
                        <span class="metric-label">RMSE</span>
                        <span class="metric-value">${metrics.rmse.toFixed(4)}</span>
                    </div>
                    <div class="metric-row">
                        <span class="metric-label">MAE</span>
                        <span class="metric-value">${metrics.mae.toFixed(4)}</span>
                    </div>
                    <div class="metric-row">
                        <span class="metric-label">Test Samples</span>
                        <span class="metric-value">${metrics.test_samples}</span>
                    </div>
                `;
            } else {
                metricsHTML = '<p style="color:#64748B; font-size:0.85rem; padding:0.5rem 0;">Metrics not yet available.</p>';
            }

            let paramsHTML = '';
            if (info.parameters && Object.keys(info.parameters).length > 0) {
                const chips = Object.entries(info.parameters)
                    .map(([k, v]) => `<span class="param-chip">${k}: ${v}</span>`)
                    .join('');
                paramsHTML = `
                    <div class="params-section">
                        <h5>Hyperparameters</h5>
                        <div>${chips}</div>
                    </div>
                `;
            }

            card.innerHTML = `
                <div class="model-card-header">
                    <h4>${label}</h4>
                    <span class="model-type-badge">${info.model_type} v${info.version}</span>
                </div>
                <div class="model-card-body">
                    ${metricsHTML}
                    ${paramsHTML}
                </div>
            `;

            grid.appendChild(card);
        });

        // Feature chips
        if (data.feature_columns && data.feature_columns.length > 0) {
            chipsContainer.innerHTML = data.feature_columns
                .map(col => `<span class="feature-chip">${col}</span>`)
                .join('');
        } else {
            chipsContainer.innerHTML = '<p style="color:#64748B;">Feature list not available.</p>';
        }
    }

    // ==================== TAB 3: SHAP ANALYSIS ====================

    function populateShap(data) {
        // Global feature importance
        if (data.global_feature_importance) {
            renderGlobalImportanceChart(data.global_feature_importance);
        }

        // Per-prediction waterfall charts
        const horizons = ['1d', '2d', '3d'];
        const predValues = {
            '1d': data.predictions['1_day'],
            '2d': data.predictions['2_days'],
            '3d': data.predictions['3_days'],
        };

        horizons.forEach(key => {
            if (data.shap_values && data.shap_values[key]) {
                renderWaterfallChart(key, data.shap_values[key], predValues[key]);
            }
        });
    }

    function renderGlobalImportanceChart(importance) {
        const canvas = document.getElementById('shapGlobalChart');
        if (!canvas) return;

        const entries = Object.entries(importance).slice(0, 15); // Top 15
        const labels = entries.map(([name]) => formatFeatureName(name));
        const values = entries.map(([, val]) => val);

        const maxVal = Math.max(...values);

        new Chart(canvas.getContext('2d'), {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Mean |SHAP| Value',
                    data: values,
                    backgroundColor: values.map(v => {
                        const intensity = 0.3 + (v / maxVal) * 0.7;
                        return `rgba(2, 132, 199, ${intensity})`;
                    }),
                    borderColor: '#0284C7',
                    borderWidth: 1,
                    borderRadius: 4,
                }],
            },
            options: {
                indexAxis: 'y',
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        backgroundColor: '#0F172A',
                        titleFont: { family: 'Inter', size: 13 },
                        bodyFont: { family: 'JetBrains Mono', size: 12 },
                        cornerRadius: 8,
                        padding: 12,
                        callbacks: {
                            label: ctx => `Mean |SHAP|: ${ctx.parsed.x.toFixed(4)}`,
                        },
                    },
                },
                scales: {
                    x: {
                        title: {
                            display: true,
                            text: 'Mean |SHAP| Value (Feature Importance)',
                            font: { family: 'Inter', size: 12, weight: '600' },
                            color: '#64748B',
                        },
                        ticks: { font: { family: 'JetBrains Mono', size: 11 }, color: '#64748B' },
                        grid: { color: 'rgba(0,0,0,0.04)' },
                    },
                    y: {
                        ticks: { font: { family: 'Inter', size: 11, weight: '500' }, color: '#1E293B' },
                        grid: { display: false },
                    },
                },
            },
        });
    }

    function renderWaterfallChart(key, shapData, predictionValue) {
        const canvas = document.getElementById(`shapWaterfall${key}`);
        const metaEl = document.getElementById(`shapMeta${key}`);
        if (!canvas) return;

        const baseValue = shapData.base_value;
        const featureValues = shapData.feature_values;

        // Sort features by absolute SHAP value (descending), take top 12
        const sorted = Object.entries(featureValues)
            .sort((a, b) => Math.abs(b[1]) - Math.abs(a[1]))
            .slice(0, 12);

        const labels = sorted.map(([name]) => formatFeatureName(name));
        const values = sorted.map(([, val]) => val);
        const colors = values.map(v => v >= 0 ? 'rgba(231, 76, 60, 0.75)' : 'rgba(52, 152, 219, 0.75)');
        const borderColors = values.map(v => v >= 0 ? '#E74C3C' : '#3498DB');

        // Meta tags
        if (metaEl) {
            metaEl.innerHTML = `
                <span class="shap-meta-tag">Base Value: ${baseValue.toFixed(2)}</span>
                <span class="shap-meta-tag">Prediction: ${Math.round(predictionValue)}</span>
                <span class="shap-meta-tag">Σ SHAP: ${values.reduce((a, b) => a + b, 0).toFixed(2)}</span>
            `;
        }

        new Chart(canvas.getContext('2d'), {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [{
                    label: 'SHAP Value',
                    data: values,
                    backgroundColor: colors,
                    borderColor: borderColors,
                    borderWidth: 1,
                    borderRadius: 4,
                }],
            },
            options: {
                indexAxis: 'y',
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        backgroundColor: '#0F172A',
                        titleFont: { family: 'Inter', size: 13 },
                        bodyFont: { family: 'JetBrains Mono', size: 12 },
                        cornerRadius: 8,
                        padding: 12,
                        callbacks: {
                            label: ctx => {
                                const v = ctx.parsed.x;
                                const dir = v >= 0 ? '↑ pushes AQI higher' : '↓ pushes AQI lower';
                                return `SHAP: ${v.toFixed(4)} (${dir})`;
                            },
                        },
                    },
                },
                scales: {
                    x: {
                        title: {
                            display: true,
                            text: 'SHAP Value (Impact on Prediction)',
                            font: { family: 'Inter', size: 12, weight: '600' },
                            color: '#64748B',
                        },
                        ticks: { font: { family: 'JetBrains Mono', size: 11 }, color: '#64748B' },
                        grid: { color: 'rgba(0,0,0,0.04)' },
                    },
                    y: {
                        ticks: { font: { family: 'Inter', size: 11, weight: '500' }, color: '#1E293B' },
                        grid: { display: false },
                    },
                },
            },
        });
    }

    // ==================== START ====================

    fetchData();

});
