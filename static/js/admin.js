// Order filtering
document.getElementById('statusFilter').addEventListener('change', filterOrders);
document.getElementById('dateFilter').addEventListener('change', filterOrders);
document.getElementById('searchOrder').addEventListener('input', filterOrders);

function filterOrders() {
    const status = document.getElementById('statusFilter').value;
    const date = document.getElementById('dateFilter').value;
    const search = document.getElementById('searchOrder').value;
    
    window.location.href = `/admin/orders?status=${status}&date=${date}&search=${search}`;
}

// View order details
function viewOrder(orderId) {
    fetch(`/admin/order/${orderId}`)
        .then(response => response.json())
        .then(order => {
            const detailsHtml = `
                <div class="row mb-3">
                    <div class="col-md-6">
                        <h6>Customer Information</h6>
                        <p>Name: ${order.customer_name}</p>
                        <p>Email: ${order.customer_email}</p>
                        <p>Phone: ${order.customer_phone || 'N/A'}</p>
                    </div>
                    <div class="col-md-6">
                        <h6>Order Information</h6>
                        <p>Order Date: ${new Date(order.created_at).toLocaleString()}</p>
                        <p>Status: <span class="badge bg-${order.status_color}">${order.status}</span></p>
                        <p>Total Amount: $${order.total_amount.toFixed(2)}</p>
                    </div>
                </div>
                <h6>Order Items</h6>
                <div class="table-responsive">
                    <table class="table">
                        <thead>
                            <tr>
                                <th>Product</th>
                                <th>Quantity</th>
                                <th>Price</th>
                                <th>Total</th>
                            </tr>
                        </thead>
                        <tbody>
                            ${order.items.map(item => `
                                <tr>
                                    <td>
                                        <img src="${item.image_url}" alt="${item.name}" style="width: 50px; height: 50px; object-fit: cover;">
                                        ${item.name}
                                    </td>
                                    <td>${item.quantity}</td>
                                    <td>$${item.price.toFixed(2)}</td>
                                    <td>$${(item.quantity * item.price).toFixed(2)}</td>
                                </tr>
                            `).join('')}
                        </tbody>
                    </table>
                </div>
            `;
            
            document.getElementById('orderDetails').innerHTML = detailsHtml;
            const modal = new bootstrap.Modal(document.getElementById('orderDetailsModal'));
            modal.show();
        });
}

// Update order status
function updateOrderStatus(orderId) {
    document.getElementById('updateOrderId').value = orderId;
    const modal = new bootstrap.Modal(document.getElementById('updateStatusModal'));
    modal.show();
}

document.getElementById('updateStatusForm').addEventListener('submit', function(e) {
    e.preventDefault();
    
    const orderId = document.getElementById('updateOrderId').value;
    const status = document.getElementById('newStatus').value;
    const note = document.getElementById('statusNote').value;
    
    fetch(`/admin/order/${orderId}/status`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ status, note })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            location.reload();
        } else {
            alert('Error updating order status');
        }
    });
});
