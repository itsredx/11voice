/**
 * PythraVirtualGrid: A client-side engine for virtual grid scrolling.
 *
 * Designed to mirror the logic of PythraVirtualList but for 2D grids.
 * Assumes a fixed number of columns (crossAxisCount) and uniform item sizes.
 */
export class PythraVirtualGrid {
    constructor(elementId, options) {
        this.container = document.getElementById(elementId);
        if (!this.container) {
            console.error(`VirtualGrid Error: Container element #${elementId} not found.`);
            return;
        }

        console.log(`✅ PythraVirtualGrid engine is initializing for #${elementId}`);

        this.options = options;
        // options.itemCount
        // options.crossAxisCount (columns)
        // options.childAspectRatio (width / height)
        // options.mainAxisSpacing
        // options.crossAxisSpacing
        // options.itemBuilderName
        // options.initialItems

        this.simplebar = new SimpleBar(this.container, this.options.simplebarOptions || {});
        this.simplebar.getScrollElement().style.overflowX = 'hidden'; // Force no horiz scroll
        this.scrollEl = this.simplebar.getScrollElement();
        this.contentEl = this.simplebar.getContentElement();

        this.itemCache = {}; // Cache will ONLY store HTML strings.
        this.visibleItemElements = [];

        // --- Calculate Layout Metrics ---
        // We need to know the width of the container to calculate item width.
        // But the container width might change on resize.
        // For now, calculate once on init. Ideally, listen for resize.
        this.itemWidth = 0;
        this.itemHeight = 0;
        this.rowHeight = 0;
        this.updateLayoutMetrics();

        // Process the initialItems object from Python.
        if (this.options.initialItems) {
            const initialCss = new Set();
            for (const index in this.options.initialItems) {
                const itemData = this.options.initialItems[index];
                this.itemCache[index] = itemData.html;
                if (itemData.css) {
                    initialCss.add(itemData.css);
                }
            }
            if (initialCss.size > 0) {
                let styleSheet = document.getElementById('virtual-list-styles');
                if (!styleSheet) {
                    styleSheet = document.createElement('style');
                    styleSheet.id = 'virtual-list-styles';
                    document.head.appendChild(styleSheet);
                }
                styleSheet.textContent += `\n${[...initialCss].join('\n')}`;
            }
        }

        // Setup DOM for virtualization
        this.sizer = document.createElement('div');
        this.sizer.style.position = 'absolute';
        this.sizer.style.top = '0';
        this.sizer.style.left = '0';
        this.sizer.style.width = '1px';
        this.updateSizerHeight(); // Set initial height
        this.contentEl.appendChild(this.sizer);
        this.contentEl.style.position = 'relative';

        this.render = this.render.bind(this);
        this.scrollEl.addEventListener('scroll', this.render);

        // Listen for window resize to recalculate grid layout
        window.addEventListener('resize', () => {
            this.updateLayoutMetrics();
            this.updateSizerHeight();
            this.render();
        });

        this.render();
    }

    updateLayoutMetrics() {
        // Get container width (minus padding if any, but scrollEl is usually the viewport)
        const containerWidth = this.scrollEl.clientWidth;
        if (containerWidth === 0) return; // Not visible yet?

        const crossAxisCount = this.options.crossAxisCount || 2;
        const mainAxisSpacing = this.options.mainAxisSpacing || 0;
        const crossAxisSpacing = this.options.crossAxisSpacing || 0;
        const childAspectRatio = this.options.childAspectRatio || 1.0;

        // Calculate item width
        // Total width = (itemWidth * count) + (spacing * (count - 1))
        // itemWidth * count = Total width - (spacing * (count - 1))
        // itemWidth = (Total width - (spacing * (count - 1))) / count
        const totalSpacing = crossAxisSpacing * (crossAxisCount - 1);
        this.itemWidth = (containerWidth - totalSpacing) / crossAxisCount;

        // Calculate item height based on aspect ratio
        this.itemHeight = this.itemWidth / childAspectRatio;

        // Store for render loop
        this.rowHeight = this.itemHeight + mainAxisSpacing;
    }

    updateSizerHeight() {
        const itemCount = this.options.itemCount;
        const crossAxisCount = this.options.crossAxisCount || 2;
        const rowCount = Math.ceil(itemCount / crossAxisCount);
        const totalHeight = (rowCount * this.rowHeight) - (this.options.mainAxisSpacing || 0); // Subtract last spacing

        this.sizer.style.height = `${totalHeight}px`;
    }

    attachEventListeners(element) {
        const clickableElements = element.querySelectorAll('[onclick]');
        clickableElements.forEach(clickable => {
            const onclickAttr = clickable.getAttribute('onclick');
            const match = onclickAttr && onclickAttr.match(/handleClick\('([^']+)'\)/);

            if (match && match[1]) {
                const callbackName = match[1];
                clickable.removeAttribute('onclick');
                clickable.addEventListener('click', () => {
                    if (window.pywebview && typeof handleClick === 'function') {
                        handleClick(callbackName);
                    }
                });
            }
        });
    }

    render() {
        if (this.rowHeight === 0) {
            this.updateLayoutMetrics();
            if (this.rowHeight === 0) return; // Still 0? Abort.
        }

        const scrollTop = this.scrollEl.scrollTop;
        const viewportHeight = this.scrollEl.clientHeight;
        const crossAxisCount = this.options.crossAxisCount || 2;
        const crossAxisSpacing = this.options.crossAxisSpacing || 0;

        // Calculate visible rows
        // Note: We use rowHeight which includes spacing
        const startRow = Math.max(0, Math.floor(scrollTop / this.rowHeight));
        // Render extra row for smooth scroll
        const endRow = Math.ceil((scrollTop + viewportHeight) / this.rowHeight) + 1;

        const itemCount = this.options.itemCount;
        // Max row index
        const maxRow = Math.ceil(itemCount / crossAxisCount) - 1;

        // Clamp
        const effectiveEndRow = Math.min(endRow, maxRow);

        // Items to render
        const itemsToRender = [];

        // Iterate visible rows
        for (let r = startRow; r <= effectiveEndRow; r++) {
            for (let c = 0; c < crossAxisCount; c++) {
                const index = (r * crossAxisCount) + c;
                if (index >= itemCount) break;

                // Calculate Position
                const top = r * this.rowHeight;
                const left = c * (this.itemWidth + crossAxisSpacing);

                itemsToRender.push({
                    index: index,
                    top: top,
                    left: left,
                    width: this.itemWidth,
                    height: this.itemHeight
                });
            }
        }

        // Sync DOM - simplistic recycling
        // Ensure we have enough elements
        while (this.visibleItemElements.length < itemsToRender.length) {
            const el = document.createElement('div');
            el.style.position = 'absolute';
            this.contentEl.appendChild(el);
            this.visibleItemElements.push(el);
        }

        // Assign items to elements
        for (let i = 0; i < itemsToRender.length; i++) {
            const item = itemsToRender[i];
            const el = this.visibleItemElements[i];

            // Update position and size
            el.style.width = `${item.width}px`;
            el.style.height = `${item.height}px`;
            el.style.transform = `translate(${item.left}px, ${item.top}px)`;
            el.style.display = 'block'; // Make sure it's visible if it was hidden

            if (el.dataset.index !== String(item.index)) {
                el.dataset.index = item.index;

                if (this.itemCache[item.index]) {
                    el.innerHTML = this.itemCache[item.index];
                    this.attachEventListeners(el);
                } else {
                    el.innerHTML = '<div style="display:flex;justify-content:center;align-items:center;height:100%;">...</div>';
                    if (window.pywebview && this.options.itemBuilderName) {
                        window.pywebview.build_list_item(this.options.itemBuilderName, item.index)
                            .then(response => {
                                const { html, css } = response;
                                this.itemCache[item.index] = html;

                                if (css) {
                                    let styleSheet = document.getElementById('virtual-list-styles');
                                    if (!styleSheet) {
                                        styleSheet = document.createElement('style');
                                        styleSheet.id = 'virtual-list-styles';
                                        document.head.appendChild(styleSheet);
                                    }
                                    if (!styleSheet.textContent.includes(css)) {
                                        styleSheet.textContent += `\n${css}`;
                                    }
                                }

                                if (el.dataset.index === String(item.index)) {
                                    el.innerHTML = html;
                                    this.attachEventListeners(el);
                                }
                            })
                            .catch(e => {
                                console.error(`Error building virtual grid item ${item.index}:`, e);
                                if (el.dataset.index === String(item.index)) {
                                    el.innerHTML = '<div>Error</div>';
                                }
                            });
                    }
                }
            }
        }

        // Hide unused elements
        for (let i = itemsToRender.length; i < this.visibleItemElements.length; i++) {
            this.visibleItemElements[i].style.display = 'none';
        }
    }

    refresh() {
        console.log(`Refreshing ALL visible items for #${this.container.id}`);
        this.itemCache = {};
        this.visibleItemElements.forEach(el => {
            el.dataset.index = '-1';
        });
        this.render();
    }

    refreshItems(indices) {
        if (!Array.isArray(indices)) return;
        indices.forEach(index => {
            if (this.itemCache[index]) {
                delete this.itemCache[index];
            }
            const visibleElement = this.visibleItemElements.find(el => el.dataset.index === String(index));
            if (visibleElement) {
                visibleElement.dataset.index = '-1';
            }
        });
        this.render();
    }

    destroy() {
        // Clean up listeners?
        // window.removeEventListener('resize', this.render); // Actually needs bound reference
        if (this.simplebar && typeof this.simplebar.unMount === 'function') {
            this.simplebar.unMount();
        }
    }
}

window.PythraVirtualGrid = PythraVirtualGrid;
