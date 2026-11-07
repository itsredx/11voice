class PythraProgressIndicator {
    constructor(id, data) {
        this.id = id;
        this.data = data;
        // Handle both element and id string
        this.element = (id instanceof HTMLElement) ? id : document.getElementById(id);


        // Initial setup
        this.init(data);
        console.log(`[PythraProgressIndicator] Initialized with id: ${id} with data:`, data);
        console.log(`[PythraProgressIndicator] Element found:`, this.element);
        this.element.className = data.class || '';

        // Set size and color if provided
        if (data.size) {
            this.element.style.width = `${data.size}px`;
            this.element.style.height = `${data.size}px`;
        }
        if (data.color) {
            this.element.style.setProperty('--loader-color', data.color);
        }
        if (data.colors) {
            if (data.colors.primary) this.element.style.setProperty('--loader-color', data.colors.primary);
            if (data.colors.secondary) this.element.style.setProperty('--loader-color-2', data.colors.secondary);
            if (data.colors.tertiary) this.element.style.setProperty('--loader-color-3', data.colors.tertiary);
            if (data.colors.bg) this.element.style.setProperty('--loader-bg', data.colors.bg);
        }
    }
    init(data) {
        this.ensureCssLoaded(data.loader);
        this.updateVisibility(data.visible);
    }

    update(data) {
        if (data.loader !== this.data.loader) {
            this.ensureCssLoaded(data.loader);
            this.data.loader = data.loader;
        }
        if (data.visible !== this.data.visible) {
            this.updateVisibility(data.visible);
            this.data.visible = data.visible;
        }
        if (data.css_vars) {
            for (const [key, value] of Object.entries(data.css_vars)) {
                this.element.style.setProperty(key, value);
            }
        }
    }

    ensureCssLoaded(loaderName) {
        const linkId = `css-loader-${loaderName}`;
        if (!document.getElementById(linkId)) {
            const link = document.createElement('link');
            link.id = linkId;
            link.rel = 'stylesheet';
            // Assuming loaders are served from standard render location or adjusted path
            // In pythra, assets are usually relative.
            // Based on package structure, it might be in 'loaders/' if copied directly 
            // OR we might need to rely on the asset server path. 
            // For now assuming 'render/loaders/' relative to the page.
            link.href = `loaders/${loaderName}.css`;
            document.head.appendChild(link);
            console.log(`[PythraProgressIndicator] Injected CSS for ${loaderName}`);

        }
    }

    updateVisibility(visible) {
        if (this.element) {
            this.element.style.display = visible ? 'inline-block' : 'none';
        }
    }

    destroy() {
        // Cleanup if needed
    }
}

if (typeof window !== 'undefined') {
    window.PythraProgressIndicator = PythraProgressIndicator;
}


