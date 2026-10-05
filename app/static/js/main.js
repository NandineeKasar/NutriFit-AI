// ------------------------------------------------------------------
// FitFuel — shared front-end behaviour
// ------------------------------------------------------------------

document.addEventListener('DOMContentLoaded', function () {

    // Show a loading overlay whenever the plan-generation form is submitted.
    // Bootstrap's built-in `novalidate` + our own check keeps native browser
    // validation working while still giving Bootstrap's styled feedback.
    var planForm = document.getElementById('planForm');
    if (planForm) {
        planForm.addEventListener('submit', function (event) {
            if (!planForm.checkValidity()) {
                event.preventDefault();
                event.stopPropagation();
                planForm.classList.add('was-validated');
                return;
            }
            var overlay = document.getElementById('global-loading-overlay');
            if (overlay) {
                overlay.classList.remove('d-none');
            }
            var submitBtn = planForm.querySelector('button[type="submit"]');
            if (submitBtn) {
                submitBtn.disabled = true;
                submitBtn.innerHTML = 'Generating your plan&hellip;';
            }
        });
    }

    // Generic: any form marked data-loading="true" shows the overlay on submit.
    document.querySelectorAll('form[data-loading="true"]').forEach(function (form) {
        form.addEventListener('submit', function () {
            if (form.checkValidity()) {
                var overlay = document.getElementById('global-loading-overlay');
                if (overlay) overlay.classList.remove('d-none');
            }
        });
    });

    // Landing page intro sequence (kept from the original design, tidied up).
    var intro = document.querySelector('.hero-intro');
    var startContainer = document.getElementById('startContainer');
    var startBtn = document.getElementById('startBtn');
    var formContainer = document.getElementById('formContainer');

    if (intro && startContainer && startBtn && formContainer) {
        setTimeout(function () {
            startContainer.classList.remove('d-none');
        }, 400);

        startBtn.addEventListener('click', function () {
            startContainer.classList.add('d-none');
            formContainer.classList.remove('d-none');
            formContainer.scrollIntoView({ behavior: 'smooth' });
        });
    }

    // Weekly plan carousel on the result page.
    var cards = document.querySelectorAll('.carousel-card');
    if (cards.length) {
        var currentIndex = 0;

        function updateCards() {
            cards.forEach(function (card) { card.classList.remove('active', 'prev', 'next'); });
            cards[currentIndex].classList.add('active');
            cards[(currentIndex - 1 + cards.length) % cards.length].classList.add('prev');
            cards[(currentIndex + 1) % cards.length].classList.add('next');
        }

        var prevBtn = document.querySelector('.prev-btn');
        var nextBtn = document.querySelector('.next-btn');
        if (prevBtn) prevBtn.addEventListener('click', function () {
            currentIndex = (currentIndex - 1 + cards.length) % cards.length;
            updateCards();
        });
        if (nextBtn) nextBtn.addEventListener('click', function () {
            currentIndex = (currentIndex + 1) % cards.length;
            updateCards();
        });

        updateCards();
    }
});
