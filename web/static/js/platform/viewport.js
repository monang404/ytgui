(function() {
    if (window.visualViewport) {
        window.visualViewport.addEventListener('resize', () => {
            const app = document.getElementById('app');
            if (app) {
                app.style.height = window.visualViewport.height + 'px';
                document.documentElement.style.setProperty("--sat", "env(safe-area-inset-top)");
                document.documentElement.style.setProperty("--sab", "env(safe-area-inset-bottom)");
            }
        });
    }
})();
