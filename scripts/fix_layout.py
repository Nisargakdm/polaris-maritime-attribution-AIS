import re

with open(r'd:\Test\polaris-maritime-attribution\backend\app\static\index.html', 'r', encoding='utf-8') as f:
    html = f.read()

# Fix the broken `</aside>` tags!
# Find the Left Sidebar section up to the <main> tag
main_split = html.split('<main class="flex-1')
if len(main_split) == 2:
    left_part = main_split[0]
    
    # Remove all </aside> from the left part, except we'll add exactly ONE at the very end of it.
    left_part = left_part.replace('</aside>', '')
    
    # Now append </aside> to the end of left_part before <main
    # left_part has trailing whitespace, let's just strip and append
    left_part = left_part.rstrip() + '\n        </aside>\n\n        <!-- Center GIS Map -->\n        <main class="flex-1'
    
    html = left_part + main_split[1]

# Make the Dashboard wider (38%)
html = html.replace('class="w-[32%] bg-navy-900 border-r', 'class="w-[38%] bg-navy-900 border-r')

# Now let's enlarge the typography specifically inside the dashboard (and header if needed, but the user said "Keep POLARIS header exactly as it is... Do not redesign it").
# To selectively target the dashboard, we can run text replacements only on `left_part`.

# But it's easier to just do it on the whole sidebar.
# Let's re-split to get just the aside content.
aside_match = re.search(r'(<aside class="w-\[38%\].*?</aside>)', html, re.DOTALL)
if aside_match:
    aside_html = aside_match.group(1)
    
    # Increase text sizes inside aside
    # text-[8px] -> text-[10px]
    aside_html = aside_html.replace('text-[8px]', 'text-[10px]')
    # text-[9px] -> text-xs
    aside_html = aside_html.replace('text-[9px]', 'text-xs')
    # text-[10px] -> text-sm
    aside_html = aside_html.replace('text-[10px]', 'text-sm')
    # text-[11px] -> text-sm (or text-base, let's use text-[15px])
    aside_html = aside_html.replace('text-[11px]', 'text-[15px]')
    # text-xs -> text-base
    aside_html = aside_html.replace('text-xs', 'text-base')
    # text-sm -> text-lg
    aside_html = aside_html.replace('text-sm', 'text-lg')
    
    # Increase icon sizes
    aside_html = aside_html.replace('w-3 h-3', 'w-4 h-4')
    aside_html = aside_html.replace('w-3.5 h-3.5', 'w-5 h-5')
    aside_html = aside_html.replace('w-4 h-4', 'w-5 h-5')
    
    # Increase paddings/margins for readability
    aside_html = aside_html.replace('space-y-1.5', 'space-y-2.5')
    aside_html = aside_html.replace('space-y-1', 'space-y-2')
    aside_html = aside_html.replace('p-2.5', 'p-4')
    aside_html = aside_html.replace('p-2 ', 'p-3 ')
    aside_html = aside_html.replace('p-3 ', 'p-4 ')
    aside_html = aside_html.replace('px-2 py-1', 'px-3 py-2')
    aside_html = aside_html.replace('px-3 py-2', 'px-4 py-3')
    
    # Increase custom width of sparklines or specific small elements if any
    aside_html = aside_html.replace('h-1.5', 'h-2.5') # Progress bars
    aside_html = aside_html.replace('h-10', 'h-16') # Sparklines
    
    html = html.replace(aside_match.group(1), aside_html)

# Also fix Playback bar sizing at the bottom if needed?
# User: "Keep Playback directly underneath the Map."
# Playback text is text-[10px] or text-xs. Let's slightly enlarge it so it matches.
main_match = re.search(r'(<div class="bg-navy-900/95 border-t.*?</div>\s*</main>)', html, re.DOTALL)
if main_match:
    pb_html = main_match.group(1)
    pb_html = pb_html.replace('text-[10px]', 'text-sm')
    pb_html = pb_html.replace('text-xs', 'text-base')
    pb_html = pb_html.replace('w-3.5 h-3.5', 'w-4 h-4')
    html = html.replace(main_match.group(1), pb_html)


with open(r'd:\Test\polaris-maritime-attribution\backend\app\static\index.html', 'w', encoding='utf-8') as f:
    f.write(html)

print("Done")
