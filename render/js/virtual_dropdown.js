

export class PythraVirtualizedDropdownInternal {
    constructor(id, options) {
        this.containerId = id;
        this.options = options;

        // The Reconciler generates dynamic IDs (e.g. fw_id_16). 
        // Best approach is finding the container using its ID, 
        // and querying the descendant label utilizing the specific CSS classes
        this.container = document.querySelector(`[data-key="${options.dropdownButtonKey}"]`);

        if (!this.container) return;

        // Find the inner label element using querySelector
        this.label = this.container.querySelector(`[data-key="${options.floatingLabelContainerKey}"]`);
        // console.log(this.label, options.key)
        // mouseover / mouseout
        // this.container.addEventListener('mouseenter', () => {
        //     console.log('Container hovered');
        //     this.updateLabelBackground();
        // });
        // this.container.addEventListener('mouseleave', () => { 
        //     console.log('Container hover end'); 
        //     this.updateLabelBackground();
        // });
        // this.container.addEventListener('click', () => { 
        //     console.log('Container clicked'); 
        // });

        // Poll computed background color via rAF — works regardless of the
        // change source (CSS class, pseudo-class, external inline style, etc.)
        let _lastBg = window.getComputedStyle(this.container).backgroundColor;
        const watchBg = () => {
            const current = window.getComputedStyle(this.container).backgroundColor;
            if (current !== _lastBg) {
                _lastBg = current;
                // console.log('Background color changed to:', current);
                this.updateLabelBackground();
            }
            this._bgWatcher = requestAnimationFrame(watchBg);
        };
        this._bgWatcher = requestAnimationFrame(watchBg);
        let _lastBr = window.getComputedStyle(this.container).border;
        const watchBr = () => {
            const current = window.getComputedStyle(this.container).border;
            // console.log(`Continer border: ${current}`)
            if (current !== _lastBr) {
                _lastBr = current;
                // console.log('Background color changed to:', current);
                this.updateLabelTop();
            }
            this._BrWatcher = requestAnimationFrame(watchBr);
        };
        this._BrWatcher = requestAnimationFrame(watchBr);
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

    updateLabelTop() {
        if (!this.container || !this.label) return;
        //floatingLabelPositionKey
        const labelPositioned = this.container.querySelector(`[data-key="${this.options.floatingLabelPositionKey}"]`);
        const borderWidthStr = window.getComputedStyle(this.container).border.slice(0, 4);
        const labelContainerHeight = window.getComputedStyle(this.label).height.replace('em', '')
            .replace('ex', '')
            .replace('%', '')
            .replace('px', '')
            .replace('cm', '')
            .replace('mm', '')
            .replace('in', '')
            .replace('pt', '')
            .replace('pc', '')
            .replace('ch', '')
            .replace('rem', '')
            .replace('vh', '')
            .replace('vw', '')
            .replace('vmin', '')
            .replace('vmax', '');
        const borderWidth = borderWidthStr.replace('em', '')
            .replace('ex', '')
            .replace('%', '')
            .replace('px', '')
            .replace('cm', '')
            .replace('mm', '')
            .replace('in', '')
            .replace('pt', '')
            .replace('pc', '')
            .replace('ch', '')
            .replace('rem', '')
            .replace('vh', '')
            .replace('vw', '')
            .replace('vmin', '')
            .replace('vmax', '') // em, ex, %, px, cm, mm, in, pt, pc, ch, rem, vh, vw, vmin, vmax
        labelPositioned.style.top = `-${borderWidthStr}`;

        if (Number(borderWidth) < Number(labelContainerHeight)) {
            var newHeight = Number(labelContainerHeight)
            this.label.style.height = `${newHeight}px`
        } else {
            var newHeight = Number(labelContainerHeight) + Number(borderWidth)
            this.label.style.height = `${Math.min(newHeight, 25)}px`
        }
        

    }


    updateLabelBackground() {
        if (!this.container || !this.label) return;
        // console.log('Updating label bg color')

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
        this.label.style.background = `${finalSolidColor}`;
        // console.log(`Continer style: ${this.container}`);
        // el = document.querySelector(`[data-role="floating-label-container"]`);
        // el.style.setProperty('--ptf-bg', color);
    }
}

window.PythraVirtualizedDropdownInternal = PythraVirtualizedDropdownInternal