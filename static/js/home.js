/**
 * Home page: dynamic hero text rotation
 */
(function() {
    function initDynamicText() {
        var textItems = document.querySelectorAll('.dynamic-text .text-item');
        if (!textItems.length) return;

        var currentIndex = 0;
        textItems[0].classList.add('active');

        setInterval(function() {
            textItems.forEach(function(item) { item.classList.remove('active'); });
            if (textItems[currentIndex]) textItems[currentIndex].classList.add('active');
            currentIndex = (currentIndex + 1) % textItems.length;
        }, 1300);
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initDynamicText);
    } else {
        initDynamicText();
    }
})();
