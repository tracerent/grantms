/**
 * Navigation: scroll detection and active link, smooth scroll to section
 */
(function() {
    function initNav() {
        var navLinks = document.querySelectorAll('.navbar-nav .nav-link[data-section]');
        if (!navLinks.length) return;

        navLinks.forEach(function(link) {
            link.addEventListener('click', function(e) {
                var section = this.getAttribute('data-section');
                if (section) {
                    var element = document.getElementById(section);
                    if (element) {
                        e.preventDefault();
                        element.scrollIntoView({ behavior: 'smooth' });
                        var navbarCollapse = document.querySelector('.navbar-collapse');
                        if (navbarCollapse && navbarCollapse.classList.contains('show')) {
                            navbarCollapse.classList.remove('show');
                        }
                    }
                }
            });
        });

        function updateActiveLink() {
            var sections = ['services', 'plans', 'resources'];
            var currentSection = sections[0];
            sections.forEach(function(section) {
                var element = document.getElementById(section);
                if (element) {
                    var rect = element.getBoundingClientRect();
                    if (rect.top <= 150) currentSection = section;
                }
            });
            navLinks.forEach(function(link) {
                link.classList.remove('active');
                if (link.getAttribute('data-section') === currentSection) {
                    link.classList.add('active');
                }
            });
        }

        window.addEventListener('scroll', updateActiveLink);
        updateActiveLink();
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initNav);
    } else {
        initNav();
    }
})();
