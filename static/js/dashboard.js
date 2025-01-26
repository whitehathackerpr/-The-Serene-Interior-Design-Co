// Toggle order details
function toggleOrderDetails(orderId) {
    const detailsDiv = document.getElementById(`orderDetails${orderId}`);
    if (detailsDiv.style.display === 'none') {
        detailsDiv.style.display = 'block';
    } else {
        detailsDiv.style.display = 'none';
    }
}

// Cancel appointment
function cancelAppointment(appointmentId) {
    if (confirm('Are you sure you want to cancel this appointment?')) {
        fetch(`/cancel_appointment/${appointmentId}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            }
        })
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                alert(data.error);
            } else {
                location.reload();
            }
        });
    }
}

// Remove from wishlist
function removeFromWishlist(productId) {
    fetch(`/remove_from_wishlist/${productId}`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.error) {
            alert(data.error);
        } else {
            location.reload();
        }
    });
}

// Appointment form validation
document.getElementById('appointmentForm').addEventListener('submit', function(e) {
    const date = new Date(document.getElementById('appointmentDate').value);
    const today = new Date();
    
    if (date < today) {
        e.preventDefault();
        alert('Please select a future date for your appointment');
    }
});

// Profile form validation
document.querySelector('form[action="/update_profile"]').addEventListener('submit', function(e) {
    const email = document.getElementById('email').value;
    const phone = document.getElementById('phone').value;
    
    if (!validateEmail(email)) {
        e.preventDefault();
        alert('Please enter a valid email address');
    }
    
    if (phone && !validatePhone(phone)) {
        e.preventDefault();
        alert('Please enter a valid phone number');
    }
});

// Validation helper functions
function validateEmail(email) {
    return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
}

function validatePhone(phone) {
    return /^\+?[\d\s-]{10,}$/.test(phone);
} 