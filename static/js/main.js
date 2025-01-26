// Product Search and Filtering
document.addEventListener('DOMContentLoaded', function() {
    const searchInput = document.getElementById('searchInput');
    const categoryFilter = document.getElementById('categoryFilter');
    const priceSort = document.getElementById('priceSort');

    function updateProducts() {
        const query = searchInput.value;
        const category = categoryFilter.value;
        const sort = priceSort.value;

        fetch(`/search_products?query=${query}&category=${category}&sort=${sort}`)
            .then(response => response.json())
            .then(products => {
                const container = document.getElementById('productsContainer');
                container.innerHTML = '';
                
                products.forEach(product => {
                    // Create product card HTML
                    const productHtml = `
                        <div class="col-md-4 mb-4">
                            <div class="card">
                                <!-- Product card content -->
                            </div>
                        </div>
                    `;
                    container.innerHTML += productHtml;
                });
            });
    }

    searchInput.addEventListener('input', updateProducts);
    categoryFilter.addEventListener('change', updateProducts);
    priceSort.addEventListener('change', updateProducts);
});

// Cart Management
function addToCart(productId) {
    fetch(`/add_to_cart/${productId}`, {
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
            alert('Product added to cart!');
            updateCartCount();
        }
    });
}

// Wishlist Management
function addToWishlist(productId) {
    fetch(`/add_to_wishlist/${productId}`, {
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
            alert('Product added to wishlist!');
            updateWishlistCount();
        }
    });
}

// Cart quantity management
document.querySelectorAll('.quantity-controls').forEach(control => {
    const decreaseBtn = control.querySelector('.decrease-qty');
    const increaseBtn = control.querySelector('.increase-qty');
    const input = control.querySelector('.quantity-input');
    const productId = control.closest('.cart-item').dataset.productId;

    decreaseBtn.addEventListener('click', () => {
        if (input.value > 1) {
            input.value = parseInt(input.value) - 1;
            updateCartQuantity(productId, input.value);
        }
    });

    increaseBtn.addEventListener('click', () => {
        input.value = parseInt(input.value) + 1;
        updateCartQuantity(productId, input.value);
    });
});

function updateCartQuantity(productId, quantity) {
    fetch('/update_cart', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            product_id: productId,
            quantity: quantity
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.error) {
            alert(data.error);
        } else {
            updateCartTotal();
        }
    });
}

// Checkout form validation
const checkoutForm = document.getElementById('checkoutForm');
if (checkoutForm) {
    checkoutForm.addEventListener('submit', function(e) {
        e.preventDefault();
        
        // Basic form validation
        const cardNumber = document.getElementById('cardNumber').value;
        const expiryDate = document.getElementById('expiryDate').value;
        const cvv = document.getElementById('cvv').value;

        if (!validateCard(cardNumber)) {
            alert('Please enter a valid card number');
            return;
        }

        if (!validateExpiry(expiryDate)) {
            alert('Please enter a valid expiry date (MM/YY)');
            return;
        }

        if (!validateCVV(cvv)) {
            alert('Please enter a valid CVV');
            return;
        }

        // If validation passes, submit the form
        this.submit();
    });
}

// Validation helper functions
function validateCard(cardNumber) {
    return /^\d{16}$/.test(cardNumber.replace(/\s/g, ''));
}

function validateExpiry(expiry) {
    return /^\d{2}\/\d{2}$/.test(expiry);
}

function validateCVV(cvv) {
    return /^\d{3,4}$/.test(cvv);
}
