// static/js/clock_in_out.js

document.addEventListener('DOMContentLoaded', function() {
    var toggleCalendarBtn = document.getElementById('toggle-calendar');
    var calendarContainer = document.getElementById('calendar-container');

    toggleCalendarBtn.addEventListener('click', function(e) {
        e.preventDefault();
        if (calendarContainer.style.display === 'none' || calendarContainer.style.display === '') {
            calendarContainer.style.display = 'block';
        } else {
            calendarContainer.style.display = 'none';
        }
    });
});
