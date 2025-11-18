// Theme Toggle Functionality
(function() {
    const themeToggle = document.getElementById('theme-toggle');
    const themeIcon = document.getElementById('theme-icon');
    const html = document.documentElement;
    
    // Load saved theme or default to light
    const savedTheme = localStorage.getItem('theme') || 'light';
    html.setAttribute('data-theme', savedTheme);
    updateIcon(savedTheme);
    
    function updateIcon(theme) {
        themeIcon.textContent = theme === 'dark' ? '☀️' : '🌙';
    }
    
    themeToggle.addEventListener('click', function() {
        const currentTheme = html.getAttribute('data-theme');
        const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
        
        html.setAttribute('data-theme', newTheme);
        localStorage.setItem('theme', newTheme);
        updateIcon(newTheme);
    });
})();

// Global SPA nav: toggle friends panel when available
(function(){
    const link = document.getElementById('nav-friends');
    if(link){ 
        link.addEventListener('click', function(e){ 
            e.preventDefault(); 
            window.dispatchEvent(new CustomEvent('toggleFriendsPanel')); 
        }); 
    }
    
    const denoiseLink = document.getElementById('nav-denoise-file');
    if(denoiseLink){ 
        denoiseLink.addEventListener('click', function(e){ 
            e.preventDefault(); 
            window.dispatchEvent(new CustomEvent('toggleDenoisePanel')); 
        }); 
    }
})();
