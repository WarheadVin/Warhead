// --- Global State and DOM Elements ---
const API_URL = "http://127.0.0.1:5000";

let cars = []; // Stores data fetched from /api/cars
let cart = []; // Stores items currently in the cart
let SHIPMENT_FEE = 3000; // Default, will be updated by API response

const productsGrid = document.getElementById('productsGrid');
const cartCountElement = document.getElementById('cartCount');
const cartItemsContainer = document.getElementById('cartItems');
const cartSubTotalElement = document.getElementById('cartSubTotal');
const cartShippingFeeElement = document.getElementById('cartShippingFee');
const cartTotalElement = document.getElementById('cartTotal');

const cartModal = document.getElementById('cartModal');
const checkoutModal = document.getElementById('checkoutModal');
const adminLoginModal = document.getElementById('adminLoginModal');
const checkoutForm = document.getElementById('checkoutForm');
const adminLoginForm = document.getElementById('adminLoginForm');


// --- Utility and State Management ---

/** Updates the cart count display in the header. */
const updateCartCount = () => {
    const totalItems = cart.reduce((total, item) => total + item.quantity, 0);
    cartCountElement.textContent = totalItems;
};

/** Calculates and displays the total cost in the cart modal, including shipping. */
const updateCartTotal = () => {
    // 1. Calculate subtotal (sum of item costs)
    const subTotal = cart.reduce((total, item) => total + (item.price * item.quantity), 0);
    
    // 2. Determine final total (Subtotal + Shipping Fee, only if cart is not empty)
    const shippingFee = cart.length > 0 ? SHIPMENT_FEE : 0;
    const finalTotal = subTotal + shippingFee;

    // 3. Update DOM elements, using toLocaleString for KSh formatting
    cartSubTotalElement.textContent = subTotal.toLocaleString('en-KE');
    cartShippingFeeElement.textContent = shippingFee.toLocaleString('en-KE');
    cartTotalElement.textContent = finalTotal.toLocaleString('en-KE');
};

/** Finds the car details from the global 'cars' list. */
const findCar = (brand, model) => {
    return cars.find(car => car.brand === brand && car.model === model);
};


// --- Product Rendering & Fetching ---

/** Creates the HTML card for a single car. */
const createCarCard = (car) => {
    const card = document.createElement('div');
    card.className = 'card';
    
    card.innerHTML = `
        <img src="${car.image}" alt="${car.brand} ${car.model}" onerror="this.onerror=null;this.src='https://placehold.co/400x150/0b6d3a/ffffff?text=Image+Missing'">
        <div class="card-body">
            <h4>${car.brand} ${car.model}</h4>
            <p class="price">KSh ${car.price.toLocaleString('en-KE')}</p>
            <p class="meta">${car.desc}</p>
            <div class="actions">
                <button class="btn btn-primary" onclick="addToCart('${car.brand}', '${car.model}')">
                    Add to Cart
                </button>
            </div>
        </div>
    `;
    productsGrid.appendChild(card);
};

/** Fetches data and renders all car cards. */
const fetchAndRenderCars = async () => {
    try {
        const response = await fetch(`${API_URL}/api/cars`);
        if (!response.ok) {
            throw new Error('Failed to fetch car data from API');
        }
        const data = await response.json();
        
        cars = data.cars; // Update global cars list
        SHIPMENT_FEE = data.shipment_fee; // Update global shipment fee

        // Render products
        productsGrid.innerHTML = ''; 
        cars.forEach(createCarCard);
        
        // Populate brand filter options
        const brands = [...new Set(cars.map(car => car.brand))].sort();
        const brandFilter = document.getElementById('brandFilter');
        brandFilter.innerHTML = '<option value="">All Brands</option>';
        brands.forEach(brand => {
            const option = document.createElement('option');
            option.value = brand;
            option.textContent = brand;
            brandFilter.appendChild(option);
        });

    } catch (error) {
        console.error("Error fetching cars:", error);
        productsGrid.innerHTML = `<p class="error-message">Error loading cars. Please ensure the Flask server is running on <a href="${API_URL}" target="_blank">${API_URL}</a>.</p>`;
    }
};


// --- Cart Management ---

/** Public function called by the 'Add to Cart' button. */
window.addToCart = (brand, model) => {
    const carDetails = findCar(brand, model);
    if (!carDetails) {
        console.error("Car not found in data:", brand, model);
        return;
    }

    const existingItem = cart.find(item => item.brand === brand && item.model === model);

    if (existingItem) {
        existingItem.quantity += 1;
    } else {
        // Use the current price from carDetails, as it might have been updated by admin
        cart.push({
            brand: carDetails.brand,
            model: carDetails.model,
            price: carDetails.price, 
            quantity: 1
        });
    }

    updateCartCount();
    console.log(`${brand} ${model} added. Cart:`, cart);
};

/** Renders the cart contents inside the cart modal. */
const renderCart = () => {
    cartItemsContainer.innerHTML = '';

    if (cart.length === 0) {
        cartItemsContainer.innerHTML = '<p>Your cart is empty.</p>';
        updateCartTotal();
        return;
    }

    cart.forEach(item => {
        const itemDiv = document.createElement('div');
        itemDiv.className = 'cart-item';
        itemDiv.innerHTML = `
            <p>
                ${item.brand} ${item.model} 
                <span class="cart-item-price">(KSh ${item.price.toLocaleString('en-KE')} x ${item.quantity})</span>
                <span class="cart-item-total">= KSh ${(item.price * item.quantity).toLocaleString('en-KE')}</span>
            </p>
        `;
        cartItemsContainer.appendChild(itemDiv);
    });

    updateCartTotal();
};


// --- Form Submission and Event Handlers ---

/** Handles the final checkout form submission to the Flask API. */
const handleCheckoutSubmit = async (event) => {
    event.preventDefault();

    if (cart.length === 0) {
        alert("Your cart is empty. Please add cars before checking out.");
        return;
    }

    const formData = new FormData(checkoutForm);
    const customerData = Object.fromEntries(formData.entries());

    // Prepare data for the Flask API
    const postData = {
        ...customerData,
        items: cart, // Attach the current cart items
    };
    
    // Send POST request to /api/order
    try {
        const response = await fetch(`${API_URL}/api/order`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(postData),
        });

        const result = await response.json();

        // Handle response
        if (response.status === 201) {
            alert(`SUCCESS! ${result.message}`);
            cart = []; // Clear the cart on successful order
            updateCartCount();
            checkoutModal.classList.add('hidden');
            checkoutForm.reset(); 
        } else if (response.status === 403) {
             // Handle Sunday closure error
             alert(`ORDER FAILED: ${result.message}`);
        }
        else {
            alert(`ERROR: ${result.message || 'Could not place order.'}`);
            console.error("API Error:", result);
        }

    } catch (error) {
        alert("A network error occurred. Check if the Flask server is running.");
        console.error("Fetch Error:", error);
    }
};

/** Handles the Admin Login form submission. */
const handleAdminLogin = async (event) => {
    event.preventDefault();

    const formData = new FormData(adminLoginForm);
    const password = formData.get('password');

    try {
        const response = await fetch(`${API_URL}/api/admin/login`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ password }),
        });

        const result = await response.json();

        if (response.status === 200 && result.success) {
            alert("Login successful! Redirecting to Admin Dashboard.");
            adminLoginModal.classList.add('hidden');
            adminLoginForm.reset();
            // Redirect to the server-rendered admin page
            window.location.href = `${API_URL}/admin/orders`; 
        } else {
            alert(result.message || 'Invalid password.');
        }
    } catch (error) {
        alert("A network error occurred. Check if the Flask server is running.");
        console.error("Login Fetch Error:", error);
    }
};

/** Initializes all event listeners. */
const initEventListeners = () => {
    // Open Cart Modal
    document.getElementById('cartBtn').addEventListener('click', () => {
        renderCart();
        cartModal.classList.remove('hidden');
    });

    // Open Admin Login Modal
    document.getElementById('adminBtn').addEventListener('click', () => {
        adminLoginModal.classList.remove('hidden');
    });

    // Close Modals (using event delegation for simplicity)
    [closeCart, closeCheckout, closeAdmin].forEach(btn => {
        btn.addEventListener('click', (e) => {
            e.target.closest('.modal').classList.add('hidden');
        });
    });

    // Proceed to Checkout
    document.getElementById('checkoutBtn').addEventListener('click', () => {
        if (cart.length > 0) {
            cartModal.classList.add('hidden'); // Close cart view
            checkoutModal.classList.remove('hidden'); // Open checkout form
        } else {
            alert("Please add items to your cart first.");
        }
    });

    // Handle Form Submissions
    checkoutForm.addEventListener('submit', handleCheckoutSubmit);
    adminLoginForm.addEventListener('submit', handleAdminLogin);

    // Set current year in footer
    document.getElementById('year').textContent = new Date().getFullYear();
    
    // Filtering logic
    document.getElementById('brandFilter').addEventListener('change', (e) => {
        const selectedBrand = e.target.value;
        const filteredCars = selectedBrand 
            ? cars.filter(car => car.brand === selectedBrand)
            : cars;

        productsGrid.innerHTML = '';
        filteredCars.forEach(createCarCard);
    });

    // Search logic
    document.getElementById('searchBar').addEventListener('input', (e) => {
        const searchTerm = e.target.value.toLowerCase();
        const filteredCars = cars.filter(car => 
            car.brand.toLowerCase().includes(searchTerm) || 
            car.model.toLowerCase().includes(searchTerm)
        );

        productsGrid.innerHTML = '';
        filteredCars.forEach(createCarCard);
    });
};


// --- Start Application ---
document.addEventListener('DOMContentLoaded', () => {
    initEventListeners();
    fetchAndRenderCars();
});