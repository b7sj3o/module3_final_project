document.addEventListener('DOMContentLoaded', function () {

    // --- Accordion toggle (product detail "Technical Specifications") ---
    document.querySelectorAll('.accordion-title').forEach(function (title) {
        title.addEventListener('click', function () {
            this.closest('.accordion-item').classList.toggle('active');
        });
    });

    // --- Quantity +/- buttons: progressive enhancement on top of a real
    // <input type="number" name="quantity" class="quantity-input">.
    // Every wrapper that carries [data-quantity-control] (the product
    // detail quantity counter, the cart line quantity selector) is wired
    // the same way: the buttons only ever change the sibling input's
    // value, they never fake add-to-cart/remove state themselves — the
    // surrounding <form> still does a real POST on submit.
    document.querySelectorAll('[data-quantity-control]').forEach(function (wrapper) {
        var input = wrapper.querySelector('.quantity-input');
        if (!input) {
            return;
        }
        var min = parseInt(input.min, 10) || 1;
        var decreaseBtn = wrapper.querySelector('[data-action="decrease"]');
        var increaseBtn = wrapper.querySelector('[data-action="increase"]');

        if (decreaseBtn) {
            decreaseBtn.addEventListener('click', function () {
                var value = parseInt(input.value, 10) || min;
                input.value = Math.max(min, value - 1);
            });
        }
        if (increaseBtn) {
            increaseBtn.addEventListener('click', function () {
                var value = parseInt(input.value, 10) || min;
                input.value = value + 1;
            });
        }
    });

});
