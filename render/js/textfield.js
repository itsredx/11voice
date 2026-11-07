export class PythraTextField {
    
    constructor(id, options) {
        this.containerId = id;
        
        // The Reconciler generates dynamic IDs (e.g. fw_id_16). 
        // Best approach is finding the container using its ID, 
        // and querying the descendant label utilizing the specific CSS classes
        this.container = document.getElementById(this.containerId);
        
        if (!this.container) return;
        
        // Find the inner label element using querySelector
        this.label = this.container.querySelector('.textfield-label');
        console.log(`text field init: ${this.label}`)
        if (!this.label) return;
        this.updateLabelBackground();

    }

    parseColor(colorStr) {
        const matches = colorStr.match(/[\d.]+/g);
        if (!matches) return [255, 255, 255, 1];
        const values = matches.map(Number);
        if (values.length === 3) values.push(1); // Default opaque alpha
        return values;
    }

    updateLabelBackground() {
        if (!this.container || !this.label) return;

        // Find the solid background color behind the container by walking up the DOM
        let parent = this.container.parentElement;
        let bgRgb = [255, 255, 255]; // Default white

        while (parent) {
            const parentBg = window.getComputedStyle(parent).backgroundColor;
            if (parentBg !== 'rgba(0, 0, 0, 0)' && parentBg !== 'transparent') {
                bgRgb = this.parseColor(parentBg);
                if (bgRgb[3] >= 0.99) { // Only stop if it's practically solid
                    break;
                }
            }
            parent = parent.parentElement;
        }

        // Get the container's designated background color
        const containerBg = window.getComputedStyle(this.container).backgroundColor;
        const fgRgba = this.parseColor(containerBg);

        // Alpha blending formula for overlaying fgRgba on bgRgb
        const alpha = fgRgba[3];
        const r = Math.round((fgRgba[0] * alpha) + (bgRgb[0] * (1 - alpha)));
        const g = Math.round((fgRgba[1] * alpha) + (bgRgb[1] * (1 - alpha)));
        const b = Math.round((fgRgba[2] * alpha) + (bgRgb[2] * (1 - alpha)));

        const finalSolidColor = `rgb(${r}, ${g}, ${b})`;


        // Apply the dynamic linear gradient to visually mask the top border cleanly
        this.label.style.background = `linear-gradient(to bottom, transparent 35%, ${finalSolidColor} 35%)`;
    }
}
