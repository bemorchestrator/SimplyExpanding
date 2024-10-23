// static/js/search_console_detail.js

document.addEventListener('DOMContentLoaded', function() {
    const data = window.searchConsoleData;

    // Parse Complex Data Structures from json_script
    const topQueriesData = JSON.parse(document.getElementById('top-queries-data').textContent);
    const topPagesData = JSON.parse(document.getElementById('top-pages-data').textContent);
    const trafficLossData = JSON.parse(document.getElementById('traffic-loss-data').textContent);

    // Handle Date Range Change
    const dateRangeSelect = document.getElementById('date-range');
    const customDateRange = document.getElementById('custom-date-range');
    const form = dateRangeSelect.closest('form'); // Assuming the select is inside the form

    if (dateRangeSelect) {
        dateRangeSelect.addEventListener('change', function() {
            if (this.value === 'custom') {
                customDateRange.classList.remove('hidden');
            } else {
                customDateRange.classList.add('hidden');
                // Update hidden input for date_range
                document.querySelector('input[name="date_range"]').value = this.value;

                // If not 'custom', clear start_date and end_date
                if (this.value !== 'custom') {
                    const startDateInput = document.getElementById('start-date');
                    const endDateInput = document.getElementById('end-date');
                    startDateInput.value = '';
                    endDateInput.value = '';
                }

                // Submit the form
                form.submit();
            }
        });
    }

    // Handle Custom Date Range Change
    const startDateInput = document.getElementById('start-date');
    const endDateInput = document.getElementById('end-date');

    function submitCustomDateRange() {
        const startDate = startDateInput.value;
        const endDate = endDateInput.value;

        if (startDate && endDate) {
            // Update hidden inputs
            document.querySelector('input[name="date_range"]').value = 'custom';
            document.querySelector('input[name="start_date"]').value = startDate;
            document.querySelector('input[name="end_date"]').value = endDate;

            // Submit the form
            form.submit();
        }
    }

    if (startDateInput && endDateInput) {
        startDateInput.addEventListener('change', submitCustomDateRange);
        endDateInput.addEventListener('change', submitCustomDateRange);
    }

    // Initialize Charts if Compare is Enabled
    if (data.compare) {
        // Function to create a line chart
        function createLineChart(ctxId, label, previousData, currentData, bgColor, borderColor) {
            const ctx = document.getElementById(ctxId).getContext('2d');
            new Chart(ctx, {
                type: 'line',
                data: {
                    labels: ['Previous', 'Current'],
                    datasets: [{
                        label: label,
                        data: [previousData, currentData],
                        backgroundColor: bgColor,
                        borderColor: borderColor,
                        borderWidth: 1,
                        fill: true,
                        tension: 0.3, // Smooth curves
                        pointRadius: 3,
                        pointBackgroundColor: borderColor
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {
                        y: { 
                            display: false, 
                            beginAtZero: true 
                        }
                    },
                    plugins: {
                        legend: { 
                            display: false 
                        }
                    },
                    elements: {
                        line: {
                            borderWidth: 2
                        }
                    }
                }
            });
        }

        // Initialize Total Clicks Chart
        if (document.getElementById('totalClicksChart')) {
            createLineChart(
                'totalClicksChart',
                'Total Clicks',
                data.previous_total_clicks,
                data.total_clicks,
                'rgba(54, 162, 235, 0.2)',
                'rgba(54, 162, 235, 1)'
            );
        }

        // Initialize Total Impressions Chart
        if (document.getElementById('totalImpressionsChart')) {
            createLineChart(
                'totalImpressionsChart',
                'Total Impressions',
                data.previous_total_impressions,
                data.total_impressions,
                'rgba(255, 206, 86, 0.2)',
                'rgba(255, 206, 86, 1)'
            );
        }

        // Initialize Total CTR Chart
        if (document.getElementById('totalCtrChart')) {
            createLineChart(
                'totalCtrChart',
                'Total CTR',
                parseFloat(data.previous_total_ctr),
                parseFloat(data.total_ctr),
                'rgba(75, 192, 192, 0.2)',
                'rgba(75, 192, 192, 1)'
            );
        }

        // Initialize Average Position Chart
        if (document.getElementById('avgPositionChart')) {
            createLineChart(
                'avgPositionChart',
                'Average Position',
                parseFloat(data.previous_avg_position),
                parseFloat(data.avg_position),
                'rgba(153, 102, 255, 0.2)',
                'rgba(153, 102, 255, 1)'
            );
        }
    }
});
