import re

with open(r'd:\Test\polaris-maritime-attribution\backend\app\static\index.html', 'r', encoding='utf-8') as f:
    html = f.read()

# Current aside tag: 
# <aside class="w-[38%] bg-navy-900 border-r border-navy-700/50 flex flex-col z-10 shrink-0 overflow-y-auto custom-scroll text-base">

# We want to change the aside to:
new_aside_tag = '<aside id="left-dashboard" class="w-[38%] bg-navy-900 border-r border-navy-700/50 flex flex-col z-20 shrink-0 overflow-hidden transition-all duration-300 relative">'

# And wrap the contents in a scrollable inner div
inner_wrapper_start = '''
    <div class="absolute top-2 right-2 z-30 opacity-100 transition-opacity duration-300" id="collapse-btn-container">
        <button id="btn-collapse-dashboard" class="p-1 bg-navy-800 hover:bg-navy-700 text-cyan-400 border border-navy-600 rounded shadow-md transition-colors flex items-center justify-center" title="Collapse dashboard" onclick="toggleDashboard()">
            <i data-lucide="chevron-left" id="icon-collapse" class="w-5 h-5"></i>
        </button>
    </div>
    <div id="dashboard-scroll-area" class="flex-1 overflow-y-auto overflow-x-hidden custom-scroll w-full transition-opacity duration-200">
        <div id="dashboard-inner-content" class="min-w-[320px] flex flex-col text-base">
'''

inner_wrapper_end = '''
        </div>
    </div>
</aside>'''

# 1. Replace the opening tag
html = re.sub(r'<aside class="w-\[38%\].*?">', new_aside_tag + inner_wrapper_start, html, count=1)

# 2. Replace the closing tag (we know there's only one now)
html = html.replace('</aside>', inner_wrapper_end)

# 3. Add the JS toggle logic at the end before </body>
js_logic = '''
        let dashboardCollapsed = false;
        function toggleDashboard() {
            const dashboard = document.getElementById('left-dashboard');
            const scrollArea = document.getElementById('dashboard-scroll-area');
            const btnIcon = document.getElementById('icon-collapse');
            const btn = document.getElementById('btn-collapse-dashboard');
            
            dashboardCollapsed = !dashboardCollapsed;
            
            if (dashboardCollapsed) {
                // Collapse
                dashboard.classList.remove('w-[38%]');
                dashboard.classList.add('w-[48px]');
                scrollArea.classList.add('opacity-0');
                scrollArea.style.pointerEvents = 'none';
                
                // Change icon
                btnIcon.setAttribute('data-lucide', 'chevron-right');
                lucide.createIcons();
                btn.setAttribute('title', 'Expand dashboard');
            } else {
                // Expand
                dashboard.classList.remove('w-[48px]');
                dashboard.classList.add('w-[38%]');
                scrollArea.classList.remove('opacity-0');
                scrollArea.style.pointerEvents = 'auto';
                
                // Change icon
                btnIcon.setAttribute('data-lucide', 'chevron-left');
                lucide.createIcons();
                btn.setAttribute('title', 'Collapse dashboard');
            }
            
            // Trigger map resize after animation
            setTimeout(() => {
                if (window.map) {
                    window.map.invalidateSize();
                } else {
                    // Try to dispatch window resize event as fallback
                    window.dispatchEvent(new Event('resize'));
                }
            }, 300);
        }
    </script>
</body>
'''
html = html.replace('</body>', js_logic)

with open(r'd:\Test\polaris-maritime-attribution\backend\app\static\index.html', 'w', encoding='utf-8') as f:
    f.write(html)

print("Done")
