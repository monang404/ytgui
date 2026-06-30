(function() {
    // Hanya aktif di desktop (pointer: fine = mouse)
    if (window.matchMedia('(pointer: fine)').matches) {
        document.addEventListener('keydown', (e) => {
            // Jangan intercept saat user mengetik di input
            if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return;

            switch (e.code) {
                case 'Space':
                    e.preventDefault();
                    if (typeof cmd === 'function') cmd('play'); // Toggle play/pause
                    break;
                case 'ArrowRight':
                    e.preventDefault();
                    if (typeof cmd === 'function') cmd('next');
                    break;
                case 'ArrowLeft':
                    e.preventDefault();
                    if (typeof cmd === 'function') cmd('prev');
                    break;
            }
        });
    }
})();
