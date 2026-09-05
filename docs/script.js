document.addEventListener('DOMContentLoaded', () => {

    // ==================== HELPERS ====================
    function getAqiDetails(aqi) {
        if (aqi <= 50) return { label: 'Good', className: 'bg-good' };
        if (aqi <= 100) return { label: 'Moderate', className: 'bg-moderate' };
        if (aqi <= 150) return { label: 'Unhealthy for Sensitive', className: 'bg-sensitive' };
        if (aqi <= 200) return { label: 'Unhealthy', className: 'bg-unhealthy' };
        return { label: 'Hazardous', className: 'bg-hazardous' };
    }

    function getHealthGuidance(aqi) {
        if (aqi <= 50) return { icon: '💚', title: 'Air quality is satisfactory', text: 'Air quality is satisfactory, and air pollution poses little or no risk. Enjoy outdoor activities normally.' };
        if (aqi <= 100) return { icon: '💛', title: 'Acceptable air quality', text: 'Air quality is acceptable. However, there may be a risk for some people, particularly those who are unusually sensitive to air pollution.' };
        if (aqi <= 150) return { icon: '🧡', title: 'Unhealthy for sensitive groups', text: 'Members of sensitive groups (children, elderly, people with respiratory diseases) may experience health effects. The general public is less likely to be affected.' };
        if (aqi <= 200) return { icon: '❤️', title: 'Unhealthy — Limit outdoor exposure', text: 'Everyone may begin to experience health effects; members of sensitive groups may experience more serious health effects. Reduce prolonged outdoor exertion.' };
        return { icon: '💜', title: 'Hazardous — Stay indoors', text: 'Health alert: The risk of health effects is increased for everyone. Avoid all outdoor physical activities. Keep windows closed.' };
    }

    function formatDate(dateString) {
        const options = { weekday: 'short', month: 'short', day: 'numeric' };
        return new Date(dateString).toLocaleDateString(undefined, options);
    }

    function formatFeatureName(name) {
        return name.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
    }

    const chartDefaults = {
        backgroundColor: '#0F172A',
        titleFont: { family: 'Inter', size: 13 },
        bodyFont: { family: 'JetBrains Mono', size: 12 },
        cornerRadius: 8,
        padding: 12,
    };

    // ==================== TAB NAVIGATION ====================
    const tabBtns = document.querySelectorAll('.tab-btn');
    const tabPanels = document.querySelectorAll('.tab-panel');

    tabBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            const target = btn.dataset.tab;
            tabBtns.forEach(b => b.classList.remove('active'));
            tabPanels.forEach(p => p.classList.remove('active'));
            btn.classList.add('active');
            const panelId = 'panel' + target.charAt(0).toUpperCase() + target.slice(1);
            document.getElementById(panelId).classList.add('active');
        });
    });

    // ==================== FETCH DATA ====================
    async function fetchData() {
        try {
            const response = await fetch('predictions.json');
            const result = await response.json();
            if (result.status === 'success') {
                populateDashboard(result);
                document.getElementById('loader').classList.add('hidden');
                document.getElementById('dashboard').classList.remove('hidden');
            } else {
                showError("Failed to load predictions.");
            }
        } catch (error) {
            console.error("Network Error:", error);
            showError("Failed to connect to the prediction API.");
        }
    }

    function showError(msg) {
        document.getElementById('loader').innerHTML = `<div style="text-align:center;color:#DC2626;padding:3rem;"><p style="font-size:1.2rem;font-weight:600;">⚠️ ${msg}</p><p style="color:#64748B;margin-top:0.5rem;">Check console for details.</p></div>`;
    }

    // ==================== MAIN POPULATE ====================
    function populateDashboard(result) {
        const data = result.data;

        // Header meta
        if (result.generated_at) {
            const genDate = new Date(result.generated_at);
            document.getElementById('lastUpdated').textContent = `⏱ Updated: ${genDate.toLocaleString()}`;
        }
        if (result.generation_time_seconds) {
            const meta = document.getElementById('headerMeta');
            const chip = document.createElement('span');
            chip.className = 'meta-chip';
            chip.textContent = `⚡ Generated in ${result.generation_time_seconds}s`;
            meta.appendChild(chip);
        }

        populateForecast(data);
        populateModels(data);
        populateShap(data);
        populateDataTab(data);
    }

    // ==================== TAB 1: FORECAST ====================
    function populateForecast(data) {
        const currentAqi = Math.round(data.current_aqi);
        const currentDetails = getAqiDetails(currentAqi);
        const guidance = getHealthGuidance(currentAqi);

        document.getElementById('currentDateLabel').textContent = `As of ${formatDate(data.current_date)}`;
        document.getElementById('currentAqiValue').textContent = currentAqi;
        document.getElementById('currentAqiCategory').textContent = currentDetails.label;
        document.getElementById('currentAqiCategory').className = `aqi-category ${currentDetails.className}`;

        // Health guidance
        document.getElementById('guidanceIcon').textContent = guidance.icon;
        document.getElementById('guidanceTitle').textContent = guidance.title;
        document.getElementById('guidanceText').textContent = guidance.text;

        // Predictions
        const preds = [
            { id: 'day1', key: '1_day', ciKey: '1d' },
            { id: 'day2', key: '2_days', ciKey: '2d' },
            { id: 'day3', key: '3_days', ciKey: '3d' },
        ];

        preds.forEach(({ id, key, ciKey }) => {
            const val = Math.round(data.predictions[key]);
            const details = getAqiDetails(val);
            document.getElementById(`${id}Value`).textContent = val;
            document.getElementById(`${id}Category`).textContent = details.label;
            document.getElementById(`${id}Category`).className = `forecast-category ${details.className}`;

            // Confidence intervals
            const ciEl = document.getElementById(`${id}Confidence`);
            if (data.prediction_intervals && data.prediction_intervals[ciKey]) {
                const ci = data.prediction_intervals[ciKey];
                ciEl.textContent = `95% CI: [${ci.ci_lower} — ${ci.ci_upper}] | σ = ${ci.std}`;
            } else if (data.predictions[`raw_${key}`] !== undefined) {
                ciEl.textContent = `Raw: ${data.predictions[`raw_${key}`]}`;
            }
        });

        renderHistoryChart(data);
    }

    function renderHistoryChart(data) {
        const ctx = document.getElementById('aqiChart').getContext('2d');
        const historyData = data.extended_history || data.history;

        const historyLabels = historyData.map(item => formatDate(item.date));
        const historyValues = historyData.map(item => Math.round(item.aqi));

        const lastDate = new Date(data.current_date);
        const futureLabels = [1, 2, 3].map(d => {
            const dt = new Date(lastDate); dt.setDate(dt.getDate() + d);
            return formatDate(dt);
        });

        const allLabels = [...historyLabels, ...futureLabels];
        const histPadded = [...historyValues, null, null, null];

        const currentAqi = Math.round(data.current_aqi);
        const p1 = Math.round(data.predictions['1_day']);
        const p2 = Math.round(data.predictions['2_days']);
        const p3 = Math.round(data.predictions['3_days']);
        const nulls = new Array(historyData.length - 1).fill(null);
        const predPadded = [...nulls, currentAqi, p1, p2, p3];

        // AQI threshold bands
        const len = allLabels.length;
        const band50 = new Array(len).fill(50);
        const band100 = new Array(len).fill(100);
        const band150 = new Array(len).fill(150);

        new Chart(ctx, {
            type: 'line',
            data: {
                labels: allLabels,
                datasets: [
                    { label: 'Good (≤50)', data: band50, borderColor: 'rgba(16,185,129,0.2)', borderWidth: 1, borderDash: [3,3], pointRadius: 0, fill: false },
                    { label: 'Moderate (≤100)', data: band100, borderColor: 'rgba(245,158,11,0.2)', borderWidth: 1, borderDash: [3,3], pointRadius: 0, fill: false },
                    { label: 'Sensitive (≤150)', data: band150, borderColor: 'rgba(239,68,68,0.2)', borderWidth: 1, borderDash: [3,3], pointRadius: 0, fill: false },
                    { label: 'Historical AQI', data: histPadded, borderColor: '#0284C7', backgroundColor: 'rgba(2,132,199,0.06)', borderWidth: 2.5, pointRadius: 3, pointBackgroundColor: '#0284C7', fill: true, tension: 0.3 },
                    { label: 'Predicted AQI', data: predPadded, borderColor: '#0F172A', borderDash: [6,4], borderWidth: 2.5, pointRadius: 5, pointBackgroundColor: '#0F172A', fill: false, tension: 0.3 },
                ],
            },
            options: {
                responsive: true, maintainAspectRatio: false,
                plugins: {
                    legend: { labels: { color: '#1E293B', font: { family: 'Inter', size: 11, weight: '600' }, usePointStyle: true, padding: 16 } },
                    tooltip: { ...chartDefaults, mode: 'index', intersect: false },
                },
                scales: {
                    x: { ticks: { color: '#64748B', font: { family: 'Inter', size: 10 }, maxRotation: 45 }, grid: { color: 'rgba(0,0,0,0.03)' } },
                    y: { beginAtZero: true, ticks: { color: '#64748B', font: { family: 'JetBrains Mono', size: 10 } }, grid: { color: 'rgba(0,0,0,0.03)' } },
                },
            },
        });
    }

    // ==================== TAB 2: MODEL DETAILS ====================
    function populateModels(data) {
        const grid = document.getElementById('modelCardsGrid');
        if (!data.model_info) { grid.innerHTML = '<p style="color:#64748B;">Model metadata not yet available. Trigger the hourly pipeline.</p>'; return; }

        const horizons = { '1d': '1-Day Forecast', '2d': '2-Day Forecast', '3d': '3-Day Forecast' };
        grid.innerHTML = '';

        Object.entries(horizons).forEach(([key, label]) => {
            const info = data.model_info[key];
            const metrics = data.evaluation_metrics?.[key];
            if (!info) return;

            const card = document.createElement('div');
            card.className = 'model-card';

            let metricsHTML = '';
            if (metrics) {
                const r2Class = metrics.r2 >= 0.8 ? 'good' : metrics.r2 >= 0.5 ? 'warning' : 'bad';
                metricsHTML = `
                    <div class="metric-row"><span class="metric-label">R² Score</span><span class="metric-value ${r2Class}">${metrics.r2.toFixed(4)}</span></div>
                    <div class="metric-row"><span class="metric-label">RMSE</span><span class="metric-value">${metrics.rmse.toFixed(4)}</span></div>
                    <div class="metric-row"><span class="metric-label">MAE</span><span class="metric-value">${metrics.mae.toFixed(4)}</span></div>
                    <div class="metric-row"><span class="metric-label">Train Samples</span><span class="metric-value">${metrics.train_samples || '—'}</span></div>
                    <div class="metric-row"><span class="metric-label">Test Samples</span><span class="metric-value">${metrics.test_samples}</span></div>`;
            } else {
                metricsHTML = '<p style="color:#64748B;font-size:0.82rem;padding:0.4rem 0;">Metrics not yet available.</p>';
            }

            let paramsHTML = '';
            if (info.parameters && Object.keys(info.parameters).length > 0) {
                const chips = Object.entries(info.parameters).map(([k, v]) => `<span class="param-chip">${k}: ${v}</span>`).join('');
                paramsHTML = `<div class="params-section"><h5>Hyperparameters</h5><div>${chips}</div></div>`;
            }

            card.innerHTML = `
                <div class="model-card-header"><h4>${label}</h4><span class="model-type-badge">${info.model_type} v${info.version}</span></div>
                <div class="model-card-body">${metricsHTML}${paramsHTML}</div>`;
            grid.appendChild(card);
        });

        // Feature chips
        const chipsContainer = document.getElementById('featureChips');
        const featureCountEl = document.getElementById('featureCount');
        if (data.feature_columns?.length) {
            featureCountEl.textContent = data.feature_columns.length;
            chipsContainer.innerHTML = data.feature_columns.map(col => `<span class="feature-chip">${col}</span>`).join('');
        }

        // Actual vs Predicted charts
        ['1d', '2d', '3d'].forEach(key => {
            const metrics = data.evaluation_metrics?.[key];
            if (metrics?.actual_vs_predicted) {
                renderActualVsPredictedChart(key, metrics.actual_vs_predicted);
            }
        });

        // Residual analysis
        populateResiduals(data);

        // Scaler table
        populateScalerTable(data);
    }

    function renderActualVsPredictedChart(key, avpData) {
        const canvas = document.getElementById(`avpChart${key}`);
        if (!canvas) return;

        const labels = avpData.map((_, i) => `#${i + 1}`);
        const actuals = avpData.map(d => d.actual);
        const predicted = avpData.map(d => d.predicted);

        new Chart(canvas.getContext('2d'), {
            type: 'line',
            data: {
                labels,
                datasets: [
                    { label: 'Actual', data: actuals, borderColor: '#059669', borderWidth: 2, pointRadius: 3, pointBackgroundColor: '#059669', tension: 0.3 },
                    { label: 'Predicted', data: predicted, borderColor: '#DC2626', borderWidth: 2, borderDash: [4, 3], pointRadius: 3, pointBackgroundColor: '#DC2626', tension: 0.3 },
                ],
            },
            options: {
                responsive: true, maintainAspectRatio: false,
                plugins: {
                    legend: { labels: { font: { family: 'Inter', size: 10 }, usePointStyle: true, padding: 10 } },
                    title: { display: true, text: `${key.toUpperCase()} — Actual vs Predicted`, font: { family: 'Inter', size: 12, weight: '700' }, color: '#0F172A' },
                    tooltip: chartDefaults,
                },
                scales: {
                    x: { ticks: { font: { size: 9 }, color: '#64748B' }, grid: { color: 'rgba(0,0,0,0.03)' } },
                    y: { ticks: { font: { family: 'JetBrains Mono', size: 10 }, color: '#64748B' }, grid: { color: 'rgba(0,0,0,0.03)' } },
                },
            },
        });
    }

    function populateResiduals(data) {
        const grid = document.getElementById('residualStatsGrid');
        if (!data.residual_analysis || Object.keys(data.residual_analysis).length === 0) {
            grid.innerHTML = '<p style="color:#64748B;grid-column:1/-1;">Residual data not yet available.</p>';
            return;
        }

        grid.innerHTML = '';
        const horizonNames = { '1d': '1-Day', '2d': '2-Day', '3d': '3-Day' };

        Object.entries(data.residual_analysis).forEach(([key, res]) => {
            const card = document.createElement('div');
            card.className = 'residual-stat-card';
            card.innerHTML = `
                <h5>${horizonNames[key]} Residuals</h5>
                <div class="residual-stat-row"><span>Mean Error</span><span>${res.mean_residual}</span></div>
                <div class="residual-stat-row"><span>Std Dev</span><span>${res.std_residual}</span></div>
                <div class="residual-stat-row"><span>Max Over-predict</span><span>${res.max_overpredict}</span></div>
                <div class="residual-stat-row"><span>Max Under-predict</span><span>${res.max_underpredict}</span></div>`;
            grid.appendChild(card);

            // Residual histogram
            if (res.residual_histogram) {
                renderResidualHistogram(key, res.residual_histogram);
            }
        });
    }

    function renderResidualHistogram(key, histogram) {
        const canvas = document.getElementById(`residualChart${key}`);
        if (!canvas) return;

        const labels = histogram.bins.slice(0, -1).map((b, i) => `${b.toFixed(0)}–${histogram.bins[i + 1].toFixed(0)}`);
        const counts = histogram.counts;

        new Chart(canvas.getContext('2d'), {
            type: 'bar',
            data: {
                labels,
                datasets: [{
                    label: 'Frequency',
                    data: counts,
                    backgroundColor: counts.map((_, i) => {
                        const mid = (histogram.bins[i] + histogram.bins[i + 1]) / 2;
                        return mid >= 0 ? 'rgba(231,76,60,0.6)' : 'rgba(52,152,219,0.6)';
                    }),
                    borderRadius: 3,
                }],
            },
            options: {
                responsive: true, maintainAspectRatio: false,
                plugins: {
                    legend: { display: false },
                    title: { display: true, text: `${key.toUpperCase()} Residual Distribution`, font: { family: 'Inter', size: 12, weight: '700' }, color: '#0F172A' },
                    tooltip: chartDefaults,
                },
                scales: {
                    x: { ticks: { font: { size: 8 }, color: '#64748B', maxRotation: 45 }, grid: { display: false } },
                    y: { ticks: { font: { family: 'JetBrains Mono', size: 10 }, color: '#64748B' }, grid: { color: 'rgba(0,0,0,0.03)' } },
                },
            },
        });
    }

    function populateScalerTable(data) {
        if (!data.scaler_info?.means || Object.keys(data.scaler_info.means).length === 0) return;

        const tbody = document.querySelector('#scalerTable tbody');
        tbody.innerHTML = '';
        Object.entries(data.scaler_info.means).forEach(([feature, mean]) => {
            const scale = data.scaler_info.scales?.[feature] || '—';
            const row = document.createElement('tr');
            row.innerHTML = `<td>${feature}</td><td>${mean}</td><td>${scale}</td>`;
            tbody.appendChild(row);
        });
    }

    // ==================== TAB 3: SHAP ====================
    function populateShap(data) {
        if (data.global_feature_importance) renderGlobalImportance(data.global_feature_importance);
        if (data.feature_correlations) renderCorrelationChart(data.feature_correlations);

        ['1d', '2d', '3d'].forEach(key => {
            if (data.shap_values?.[key]) {
                const predVal = { '1d': data.predictions['1_day'], '2d': data.predictions['2_days'], '3d': data.predictions['3_days'] }[key];
                renderWaterfall(key, data.shap_values[key], predVal);
            }
        });

        // Latest feature values table
        populateLatestFeaturesTable(data);
    }

    function renderGlobalImportance(importance) {
        const canvas = document.getElementById('shapGlobalChart');
        if (!canvas) return;

        const entries = Object.entries(importance).slice(0, 15);
        const labels = entries.map(([name]) => formatFeatureName(name));
        const values = entries.map(([, val]) => val);
        const maxVal = Math.max(...values);

        new Chart(canvas.getContext('2d'), {
            type: 'bar',
            data: {
                labels,
                datasets: [{
                    label: 'Mean |SHAP|',
                    data: values,
                    backgroundColor: values.map(v => `rgba(2,132,199,${0.3 + (v / maxVal) * 0.7})`),
                    borderColor: '#0284C7', borderWidth: 1, borderRadius: 4,
                }],
            },
            options: {
                indexAxis: 'y', responsive: true, maintainAspectRatio: false,
                plugins: { legend: { display: false }, tooltip: { ...chartDefaults, callbacks: { label: ctx => `Mean |SHAP|: ${ctx.parsed.x.toFixed(4)}` } } },
                scales: {
                    x: { title: { display: true, text: 'Mean |SHAP| Value (Feature Importance)', font: { family: 'Inter', size: 11, weight: '600' }, color: '#64748B' }, ticks: { font: { family: 'JetBrains Mono', size: 10 }, color: '#64748B' }, grid: { color: 'rgba(0,0,0,0.03)' } },
                    y: { ticks: { font: { family: 'Inter', size: 10, weight: '500' }, color: '#1E293B' }, grid: { display: false } },
                },
            },
        });
    }

    function renderCorrelationChart(correlations) {
        const canvas = document.getElementById('correlationChart');
        if (!canvas) return;

        const entries = Object.entries(correlations).slice(0, 15);
        const labels = entries.map(([name]) => formatFeatureName(name));
        const values = entries.map(([, val]) => val);

        new Chart(canvas.getContext('2d'), {
            type: 'bar',
            data: {
                labels,
                datasets: [{
                    label: 'Correlation with AQI',
                    data: values,
                    backgroundColor: values.map(v => v >= 0 ? 'rgba(231,76,60,0.65)' : 'rgba(52,152,219,0.65)'),
                    borderColor: values.map(v => v >= 0 ? '#E74C3C' : '#3498DB'),
                    borderWidth: 1, borderRadius: 4,
                }],
            },
            options: {
                indexAxis: 'y', responsive: true, maintainAspectRatio: false,
                plugins: {
                    legend: { display: false },
                    tooltip: { ...chartDefaults, callbacks: { label: ctx => { const v = ctx.parsed.x; return `Correlation: ${v.toFixed(4)} (${v >= 0 ? 'positive' : 'negative'})`; } } },
                },
                scales: {
                    x: { title: { display: true, text: 'Pearson Correlation Coefficient', font: { family: 'Inter', size: 11, weight: '600' }, color: '#64748B' }, ticks: { font: { family: 'JetBrains Mono', size: 10 }, color: '#64748B' }, grid: { color: 'rgba(0,0,0,0.03)' }, min: -1, max: 1 },
                    y: { ticks: { font: { family: 'Inter', size: 10, weight: '500' }, color: '#1E293B' }, grid: { display: false } },
                },
            },
        });
    }

    function renderWaterfall(key, shapData, predictionValue) {
        const canvas = document.getElementById(`shapWaterfall${key}`);
        const metaEl = document.getElementById(`shapMeta${key}`);
        if (!canvas) return;

        const sorted = Object.entries(shapData.feature_values).sort((a, b) => Math.abs(b[1]) - Math.abs(a[1])).slice(0, 12);
        const labels = sorted.map(([name]) => formatFeatureName(name));
        const values = sorted.map(([, val]) => val);

        if (metaEl) {
            metaEl.innerHTML = `
                <span class="shap-meta-tag">Base: ${shapData.base_value.toFixed(2)}</span>
                <span class="shap-meta-tag">Prediction: ${Math.round(predictionValue)}</span>
                <span class="shap-meta-tag">Σ SHAP: ${values.reduce((a, b) => a + b, 0).toFixed(2)}</span>
                <span class="shap-meta-tag">Top ${sorted.length} features</span>`;
        }

        new Chart(canvas.getContext('2d'), {
            type: 'bar',
            data: {
                labels,
                datasets: [{
                    label: 'SHAP Value',
                    data: values,
                    backgroundColor: values.map(v => v >= 0 ? 'rgba(231,76,60,0.7)' : 'rgba(52,152,219,0.7)'),
                    borderColor: values.map(v => v >= 0 ? '#E74C3C' : '#3498DB'),
                    borderWidth: 1, borderRadius: 4,
                }],
            },
            options: {
                indexAxis: 'y', responsive: true, maintainAspectRatio: false,
                plugins: { legend: { display: false }, tooltip: { ...chartDefaults, callbacks: { label: ctx => { const v = ctx.parsed.x; return `SHAP: ${v.toFixed(4)} (${v >= 0 ? '↑ higher AQI' : '↓ lower AQI'})`; } } } },
                scales: {
                    x: { title: { display: true, text: 'SHAP Value (Impact on Prediction)', font: { family: 'Inter', size: 11, weight: '600' }, color: '#64748B' }, ticks: { font: { family: 'JetBrains Mono', size: 10 }, color: '#64748B' }, grid: { color: 'rgba(0,0,0,0.03)' } },
                    y: { ticks: { font: { family: 'Inter', size: 10, weight: '500' }, color: '#1E293B' }, grid: { display: false } },
                },
            },
        });
    }

    function populateLatestFeaturesTable(data) {
        const tbody = document.querySelector('#latestFeaturesTable tbody');
        if (!tbody || !data.latest_feature_values) return;

        tbody.innerHTML = '';
        const features = data.feature_columns || Object.keys(data.latest_feature_values);

        features.forEach(feat => {
            const row = document.createElement('tr');
            const rawVal = data.latest_feature_values?.[feat] ?? '—';
            const shap1d = data.shap_values?.['1d']?.feature_values?.[feat] ?? '—';
            const shap2d = data.shap_values?.['2d']?.feature_values?.[feat] ?? '—';
            const shap3d = data.shap_values?.['3d']?.feature_values?.[feat] ?? '—';

            const colorCell = (v) => {
                if (v === '—') return '<td>—</td>';
                const color = v >= 0 ? '#E74C3C' : '#3498DB';
                return `<td style="color:${color};font-weight:600;">${v}</td>`;
            };

            row.innerHTML = `<td>${feat}</td><td>${rawVal}</td>${colorCell(shap1d)}${colorCell(shap2d)}${colorCell(shap3d)}`;
            tbody.appendChild(row);
        });
    }

    // ==================== TAB 4: DATA & FEATURES ====================
    function populateDataTab(data) {
        // Dataset stats
        const statsGrid = document.getElementById('datasetStatsGrid');
        if (data.dataset_statistics) {
            const ds = data.dataset_statistics;
            const aqiStats = ds.aqi_statistics || {};
            statsGrid.innerHTML = `
                <div class="stat-card"><div class="stat-value">${ds.total_rows?.toLocaleString() || '—'}</div><div class="stat-label">Total Data Points</div></div>
                <div class="stat-card"><div class="stat-value">${aqiStats.mean || '—'}</div><div class="stat-label">Mean AQI</div></div>
                <div class="stat-card"><div class="stat-value">${aqiStats.median || '—'}</div><div class="stat-label">Median AQI</div></div>
                <div class="stat-card"><div class="stat-value">${aqiStats.std || '—'}</div><div class="stat-label">Std Dev</div></div>
                <div class="stat-card"><div class="stat-value">${aqiStats.min || '—'}</div><div class="stat-label">Min AQI</div></div>
                <div class="stat-card"><div class="stat-value">${aqiStats.max || '—'}</div><div class="stat-label">Max AQI</div></div>
                <div class="stat-card"><div class="stat-value">${aqiStats.q25 || '—'}</div><div class="stat-label">25th Percentile</div></div>
                <div class="stat-card"><div class="stat-value">${aqiStats.q75 || '—'}</div><div class="stat-label">75th Percentile</div></div>`;

            // AQI distribution chart
            if (ds.aqi_distribution) renderAqiDistribution(ds.aqi_distribution);
        }

        // Data sources
        const sourcesGrid = document.getElementById('dataSourcesGrid');
        if (data.pipeline_info?.data_source) {
            sourcesGrid.innerHTML = `
                <div class="data-source-item"><h4>🏭 Air Pollution Data</h4><p><strong>Source:</strong> ${data.pipeline_info.data_source.pollution}<br><strong>Endpoint:</strong> /data/2.5/air_pollution/history<br><strong>Pollutants:</strong> PM2.5, PM10, O3, NO2, SO2, CO, NO, NH3<br><strong>AQI Conversion:</strong> US EPA breakpoint tables (epa_aqi.py)</p></div>
                <div class="data-source-item"><h4>🌤️ Weather Data</h4><p><strong>Source:</strong> ${data.pipeline_info.data_source.weather}<br><strong>Features:</strong> Temperature (°C), Relative Humidity (%), Wind Speed (km/h)<br><strong>Coverage:</strong> Archive API + Forecast API (no lag)</p></div>`;
        }

        // Pollutant chips
        const pollutantChips = document.getElementById('pollutantChips');
        if (data.pipeline_info?.pollutants_tracked) {
            pollutantChips.innerHTML = data.pipeline_info.pollutants_tracked.map(p => `<div class="pollutant-chip">${p}</div>`).join('');
        }

        // Feature engineering items
        const featureEngList = document.getElementById('featureEngList');
        if (data.pipeline_info?.feature_engineering) {
            featureEngList.innerHTML = data.pipeline_info.feature_engineering.map(f => {
                const [codePart, ...descParts] = f.split(' — ');
                return `<div class="feature-eng-item"><code>${codePart}</code><span>— ${descParts.join(' — ')}</span></div>`;
            }).join('');
        }

        // Feature statistics table
        if (data.dataset_statistics?.feature_statistics) {
            const tbody = document.querySelector('#featureStatsTable tbody');
            tbody.innerHTML = '';
            Object.entries(data.dataset_statistics.feature_statistics).forEach(([feat, stats]) => {
                const row = document.createElement('tr');
                row.innerHTML = `<td>${feat}</td><td>${stats.mean}</td><td>${stats.std}</td><td>${stats.min}</td><td>${stats.max}</td>`;
                tbody.appendChild(row);
            });
        }

        // Missing values
        const missingCard = document.getElementById('missingValuesCard');
        const missingContent = document.getElementById('missingValuesContent');
        if (data.dataset_statistics?.missing_values && Object.keys(data.dataset_statistics.missing_values).length > 0) {
            let html = '<div style="display:flex;flex-wrap:wrap;gap:0.5rem;padding:0.5rem 0;">';
            Object.entries(data.dataset_statistics.missing_values).forEach(([col, count]) => {
                html += `<span class="param-chip" style="border-color:#FECACA;background:#FEF2F2;color:#991B1B;">${col}: ${count} missing</span>`;
            });
            html += '</div>';
            missingContent.innerHTML = html;
        } else {
            missingContent.innerHTML = '<p style="color:#059669;font-weight:600;padding:0.5rem 0;">✅ No missing values detected in any column!</p>';
        }
    }

    function renderAqiDistribution(distribution) {
        const canvas = document.getElementById('aqiDistChart');
        if (!canvas) return;

        const labels = Object.keys(distribution);
        const values = Object.values(distribution);
        const colors = ['#D1FAE5', '#FEF3C7', '#FFEDD5', '#FEE2E2', '#FCE7F3', '#F3E8FF'];
        const borderColors = ['#059669', '#D97706', '#EA580C', '#DC2626', '#DB2777', '#7C3AED'];

        new Chart(canvas.getContext('2d'), {
            type: 'doughnut',
            data: {
                labels,
                datasets: [{
                    data: values,
                    backgroundColor: colors,
                    borderColor: borderColors,
                    borderWidth: 2,
                }],
            },
            options: {
                responsive: true, maintainAspectRatio: false,
                plugins: {
                    legend: { position: 'right', labels: { font: { family: 'Inter', size: 11 }, padding: 12, usePointStyle: true } },
                    tooltip: { ...chartDefaults, callbacks: { label: ctx => { const total = values.reduce((a, b) => a + b, 0); const pct = ((ctx.parsed / total) * 100).toFixed(1); return `${ctx.label}: ${ctx.parsed} readings (${pct}%)`; } } },
                },
            },
        });
    }

    // ==================== START ====================
    fetchData();
});
