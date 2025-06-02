// Initialize Socket.IO
const socket = io();

// Chart.js configuration
let hourlyChart = null;

// Theme colors
const THEME = {
    darkGreen: '#1a472a',
    lightGreen: '#2d5a3f',
    white: '#ffffff'
};

// Update current time
function updateCurrentTime() {
    const now = new Date();
    document.getElementById('current-time').textContent = now.toLocaleString();
}

// Initialize hourly statistics chart
function initHourlyChart(data) {
    const ctx = document.getElementById('hourlyChart').getContext('2d');
    
    if (hourlyChart) {
        hourlyChart.destroy();
    }

    hourlyChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: data.labels,
            datasets: [{
                label: 'Vehicles',
                data: data.values,
                borderColor: 'rgb(75, 192, 192)',
                backgroundColor: 'rgba(75, 192, 192, 0.1)',
                tension: 0.1,
                fill: true,
                pointBackgroundColor: 'rgb(75, 192, 192)',
                pointBorderColor: '#fff',
                pointHoverBackgroundColor: '#fff',
                pointHoverBorderColor: 'rgb(75, 192, 192)',
                borderWidth: 2,
                pointRadius: 4,
                pointHoverRadius: 6
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            layout: {
                padding: {
                    top: 10,
                    right: 20,
                    bottom: 10,
                    left: 10
                }
            },
            plugins: {
                legend: {
                    display: false
                },
                title: {
                    display: true,
                    text: 'Hourly Parking Statistics',
                    color: '#333',
                    font: {
                        size: 16,
                        weight: 'normal'
                    },
                    padding: 20
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: {
                        stepSize: 1,
                        color: '#666',
                        font: {
                            size: 12
                        }
                    },
                    grid: {
                        color: 'rgba(0, 0, 0, 0.05)',
                        drawBorder: false
                    }
                },
                x: {
                    ticks: {
                        color: '#666',
                        font: {
                            size: 12
                        },
                        maxRotation: 45,
                        minRotation: 45
                    },
                    grid: {
                        display: false
                    }
                }
            },
            interaction: {
                intersect: false,
                mode: 'index'
            },
            elements: {
                line: {
                    tension: 0.3
                }
            }
        }
    });
}

// Update recent activities
function updateRecentActivities(activities) {
    const container = document.getElementById('recent-activities');
    container.innerHTML = '';

    activities.forEach(activity => {
        const item = document.createElement('div');
        item.className = 'list-group-item';
        item.innerHTML = `
            <div class="d-flex w-100 justify-content-between">
                <h6 class="mb-1" style="color: ${THEME.darkGreen};">${activity.plate_number}</h6>
                <small style="color: ${THEME.lightGreen};">${new Date(activity.timestamp).toLocaleTimeString()}</small>
            </div>
            <p class="mb-1" style="color: ${THEME.darkGreen};">${activity.action}</p>
        `;
        container.appendChild(item);
    });
}

// Update unauthorized attempts table
function updateUnauthorizedAttempts(attempts) {
    const tbody = document.getElementById('unauthorized-attempts');
    tbody.innerHTML = '';

    attempts.forEach(attempt => {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td>${new Date(attempt.timestamp).toLocaleString()}</td>
            <td>${attempt.plate_number}</td>
            <td>${attempt.gate_location}</td>
            <td><span class="badge bg-danger">Unauthorized</span></td>
        `;
        tbody.appendChild(row);
    });
}

// Update dashboard statistics
function updateStats(data) {
    document.getElementById('occupancy-count').textContent = data.occupancy;
    document.getElementById('revenue').textContent = data.revenue.toLocaleString();
    document.getElementById('available-spaces').textContent = 50 - data.occupancy;
    document.getElementById('unauthorized-count').textContent = data.unauthorized_attempts.length;
}

// Fetch initial data
async function fetchInitialData() {
    try {
        const [statsResponse, hourlyResponse] = await Promise.all([
            fetch('/api/parking_stats'),
            fetch('/api/hourly_stats')
        ]);

        const stats = await statsResponse.json();
        const hourlyData = await hourlyResponse.json();

        updateStats(stats);
        updateRecentActivities(stats.recent_activities);
        updateUnauthorizedAttempts(stats.unauthorized_attempts);
        initHourlyChart(hourlyData);
    } catch (error) {
        console.error('Error fetching initial data:', error);
    }
}

// Socket.IO event handlers
socket.on('connect', () => {
    console.log('Connected to server');
});

socket.on('update', (data) => {
    switch(data.type) {
        case 'stats':
            updateStats(data.data);
            break;
        case 'activities':
            updateRecentActivities(data.data);
            break;
        case 'unauthorized':
            updateUnauthorizedAttempts(data.data);
            break;
        case 'hourly':
            initHourlyChart(data.data);
            break;
    }
});

// Initialize dashboard
document.addEventListener('DOMContentLoaded', () => {
    // Update time every second
    updateCurrentTime();
    setInterval(updateCurrentTime, 1000);

    // Fetch initial data
    fetchInitialData();

    // Refresh data every 30 seconds
    setInterval(fetchInitialData, 30000);
}); 