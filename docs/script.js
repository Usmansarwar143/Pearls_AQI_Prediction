document.addEventListener('DOMContentLoaded', () => {
    
    // Helper: Determine AQI Category and CSS Class
    function getAqiDetails(aqi) {
        if (aqi <= 50) return { label: 'Good', className: 'bg-good' };
        if (aqi <= 100) return { label: 'Moderate', className: 'bg-moderate' };
        if (aqi <= 150) return { label: 'Unhealthy for Sensitive', className: 'bg-sensitive' };
        if (aqi <= 200) return { label: 'Unhealthy', className: 'bg-unhealthy' };
        return { label: 'Hazardous', className: 'bg-hazardous' };
    }

    // Helper: Format Date
    function formatDate(dateString) {
        const options = { weekday: 'short', month: 'short', day: 'numeric' };
        return new Date(dateString).toLocaleDateString(undefined, options);
    }

    // Fetch Data from API
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
                alert("Failed to load predictions: " + result.message);
            }
        } catch (error) {
            console.error("Network Error:", error);
            alert("Failed to connect to the prediction API.");
        }
    }

    // Populate the UI
    function populateDashboard(data) {
        
        // 1. Current AQI
        const currentAqi = Math.round(data.current_aqi);
        const currentDetails = getAqiDetails(currentAqi);
        
        document.getElementById('currentDateLabel').textContent = `As of ${formatDate(data.current_date)}`;
        document.getElementById('currentAqiValue').textContent = currentAqi;
        document.getElementById('currentAqiCategory').textContent = currentDetails.label;
        document.getElementById('currentAqiCategory').className = `aqi-category ${currentDetails.className}`;

        // 2. Predictions
        const p1 = Math.round(data.predictions['1_day']);
        const p2 = Math.round(data.predictions['2_days']);
        const p3 = Math.round(data.predictions['3_days']);

        const p1Details = getAqiDetails(p1);
        const p2Details = getAqiDetails(p2);
        const p3Details = getAqiDetails(p3);

        document.getElementById('day1Value').textContent = p1;
        document.getElementById('day1Category').textContent = p1Details.label;
        document.getElementById('day1Category').className = `forecast-category ${p1Details.className}`;

        document.getElementById('day2Value').textContent = p2;
        document.getElementById('day2Category').textContent = p2Details.label;
        document.getElementById('day2Category').className = `forecast-category ${p2Details.className}`;

        document.getElementById('day3Value').textContent = p3;
        document.getElementById('day3Category').textContent = p3Details.label;
        document.getElementById('day3Category').className = `forecast-category ${p3Details.className}`;

        // 3. Render Chart
        renderChart(data);
    }

    // Render Chart.js
    function renderChart(data) {
        const ctx = document.getElementById('aqiChart').getContext('2d');
        
        // Combine history and predictions for a continuous line
        const historyLabels = data.history.map(item => formatDate(item.date));
        const historyData = data.history.map(item => Math.round(item.aqi));
        
        // Future dates
        const lastDate = new Date(data.current_date);
        const day1Date = new Date(lastDate); day1Date.setDate(day1Date.getDate() + 1);
        const day2Date = new Date(lastDate); day2Date.setDate(day2Date.getDate() + 2);
        const day3Date = new Date(lastDate); day3Date.setDate(day3Date.getDate() + 3);

        const allLabels = [...historyLabels, formatDate(day1Date), formatDate(day2Date), formatDate(day3Date)];
        
        // We pad the historical data array with nulls for the future, and pad the future array with nulls for the past
        const histDataPadded = [...historyData, null, null, null];
        
        // To make the line continuous, the prediction line must start at the current day's AQI
        const currentAqi = Math.round(data.current_aqi);
        const p1 = Math.round(data.predictions['1_day']);
        const p2 = Math.round(data.predictions['2_days']);
        const p3 = Math.round(data.predictions['3_days']);

        // Null padding array the size of history - 1
        const nulls = new Array(data.history.length - 1).fill(null);
        const predDataPadded = [...nulls, currentAqi, p1, p2, p3];

        const chartConfig = {
            type: 'line',
            data: {
                labels: allLabels,
                datasets: [
                    {
                        label: 'Historical AQI',
                        data: histDataPadded,
                        borderColor: '#98C1D9',
                        backgroundColor: 'rgba(152, 193, 217, 0.2)',
                        borderWidth: 3,
                        pointRadius: 4,
                        fill: true,
                        tension: 0.3
                    },
                    {
                        label: 'Predicted AQI',
                        data: predDataPadded,
                        borderColor: '#3D5A80',
                        borderDash: [5, 5], // dashed line for future
                        borderWidth: 3,
                        pointRadius: 5,
                        pointBackgroundColor: '#3D5A80',
                        fill: false,
                        tension: 0.3
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        labels: {
                            color: '#333333',
                            font: { family: 'Poppins', size: 14 }
                        }
                    },
                    tooltip: {
                        mode: 'index',
                        intersect: false,
                        titleFont: { family: 'Poppins', size: 14 },
                        bodyFont: { family: 'Fira Code', size: 13 }
                    }
                },
                scales: {
                    x: {
                        ticks: {
                            color: '#333333',
                            font: { family: 'Poppins' }
                        },
                        grid: {
                            color: 'rgba(128, 128, 128, 0.2)'
                        }
                    },
                    y: {
                        beginAtZero: true,
                        ticks: {
                            color: '#333333',
                            font: { family: 'Fira Code' }
                        },
                        grid: {
                            color: 'rgba(128, 128, 128, 0.2)'
                        }
                    }
                }
            }
        };

        window.aqiChartInstance = new Chart(ctx, chartConfig);
    }

    // Start!
    fetchData();

});
