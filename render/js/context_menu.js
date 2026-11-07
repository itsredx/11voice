const _ctxMenuDefaults = {
    panel: {
        backgroundColor: '#2d2d2d',
        borderColor: '#555',
        borderRadius: '6px',
        borderWidth: '1px',
        boxShadow: '0 4px 16px rgba(0,0,0,0.4)',
    },
    item: {
        color: '#eee',
        fontSize: '13px',
        fontFamily: 'sans-serif',
        padding: '6px 16px',
        hoverBackgroundColor: '#3d3d3d',
        disabledOpacity: 0.4,
    },
    icon: {
        size: '18px',
        color: null,
    },
    divider: {
        color: '#555',
        margin: '4px 0',
    },
};

function _mergeTheme(user) {
    const t = {};
    for (const key of ['panel', 'item', 'icon', 'divider']) {
        t[key] = { ..._ctxMenuDefaults[key], ...(user?.[key] || {}) };
    }
    return t;
}

export class PythraContextMenuInternal {
    constructor(element, options) {
        this.element = (element instanceof HTMLElement) ? element : document.getElementById(element);
        if (!this.element) {
            console.error('PythraContextMenu: element not found');
            return;
        }

        this.options = options || {};
        this.menuEl = null;
        this.menuItems = this.options.items || [];
        this.theme = _mergeTheme(this.options.theme);
        this.active = false;

        this._onContextMenu = this._onContextMenu.bind(this);
        this._onClickOutside = this._onClickOutside.bind(this);
        this._onKeyDown = this._onKeyDown.bind(this);

        this.element.addEventListener('contextmenu', this._onContextMenu);
    }

    // ── Build ────────────────────────────────────────────────────────────────

    _buildMenu() {
        const t = this.theme;

        this.menuEl = document.createElement('div');
        this.menuEl.className = 'pythra-context-menu';
        this.menuEl.style.cssText = `
            position: fixed;
            z-index: 999999;
            display: none;
            min-width: 180px;
            max-width: 280px;
            padding: 4px 0;
            background: ${t.panel.backgroundColor};
            border: ${t.panel.borderWidth} solid ${t.panel.borderColor};
            border-radius: ${t.panel.borderRadius};
            box-shadow: ${t.panel.boxShadow};
            font-family: ${t.item.fontFamily};
            font-size: ${t.item.fontSize};
            color: ${t.item.color};
            user-select: none;
            -webkit-user-select: none;
        `;

        this.menuItems.forEach((item, i) => {
            if (item.divider) {
                const divider = document.createElement('div');
                divider.style.cssText = `
                    height: 1px;
                    background: ${t.divider.color};
                    margin: ${t.divider.margin};
                `;
                this.menuEl.appendChild(divider);
                return;
            }

            const itemEl = document.createElement('div');
            itemEl.className = 'pythra-context-menu-item';
            itemEl.dataset.index = i;
            itemEl.style.cssText = `
                display: flex;
                align-items: center;
                padding: ${t.item.padding};
                cursor: ${item.enabled !== false ? 'pointer' : 'default'};
                opacity: ${item.enabled !== false ? '1' : t.item.disabledOpacity};
                transition: background 0.12s;
            `;

            if (item.icon) {
                const iconEl = document.createElement('span');
                const fontFamily = item.fontFamily || 'Material Symbols Outlined';
                iconEl.textContent = item.icon;
                iconEl.style.cssText = `
                    font-family: '${fontFamily}';
                    font-weight: normal;
                    font-style: normal;
                    font-size: ${t.icon.size};
                    margin-right: 12px;
                    width: ${t.icon.size};
                    text-align: center;
                    line-height: 1;
                    letter-spacing: normal;
                    text-transform: none;
                    display: inline-block;
                    white-space: nowrap;
                    word-wrap: normal;
                    direction: ltr;
                    -webkit-font-smoothing: antialiased;
                    text-rendering: optimizeLegibility;
                    -moz-osx-font-smoothing: grayscale;
                    font-feature-settings: 'liga';
                    ${t.icon.color ? `color: ${t.icon.color};` : ''}
                `;
                itemEl.appendChild(iconEl);
            } else {
                const spacer = document.createElement('span');
                spacer.style.cssText = 'display:inline-block;width:30px;';
                itemEl.appendChild(spacer);
            }

            const labelEl = document.createElement('span');
            labelEl.style.cssText = 'flex:1;';
            labelEl.textContent = item.label;
            itemEl.appendChild(labelEl);

            if (item.shortcut) {
                const shortcutEl = document.createElement('span');
                shortcutEl.style.cssText = 'margin-left:16px;color:#888;font-size:11px;';
                shortcutEl.textContent = item.shortcut;
                itemEl.appendChild(shortcutEl);
            }

            itemEl.addEventListener('mouseenter', () => {
                if (item.enabled !== false) {
                    itemEl.style.background = t.item.hoverBackgroundColor;
                }
            });
            itemEl.addEventListener('mouseleave', () => {
                itemEl.style.background = 'transparent';
            });

            itemEl.addEventListener('click', (ev) => {
                ev.stopPropagation();
                if (item.enabled === false) return;
                this._hide();
                if (item.cb && window.pywebview) {
                    window.pywebview.on_pressed_str(item.cb);
                }
            });

            this.menuEl.appendChild(itemEl);
        });

        document.body.appendChild(this.menuEl);
    }

    _updateItemStates() {
        if (!this.menuEl) return;
        const t = this.theme;
        const items = this.menuEl.querySelectorAll('.pythra-context-menu-item');
        items.forEach((el, i) => {
            const item = this.menuItems[i];
            if (!item) return;
            el.style.opacity = item.enabled !== false ? '1' : t.item.disabledOpacity;
            el.style.cursor = item.enabled !== false ? 'pointer' : 'default';
        });
    }

    _positionMenu(x, y) {
        if (!this.menuEl) return;
        const vw = window.innerWidth;
        const vh = window.innerHeight;
        const mw = this.menuEl.offsetWidth || 200;
        const mh = this.menuEl.offsetHeight || 200;

        let left = x;
        let top = y;

        if (left + mw > vw) left = vw - mw - 8;
        if (top + mh > vh) top = vh - mh - 8;
        if (left < 0) left = 8;
        if (top < 0) top = 8;

        this.menuEl.style.left = left + 'px';
        this.menuEl.style.top = top + 'px';
    }

    _show() {
        if (this.menuEl) {
            this.menuEl.style.display = 'block';
            this.active = true;
        }
    }

    _hide() {
        if (this.menuEl) {
            this.menuEl.style.display = 'none';
            this.active = false;
        }
        document.removeEventListener('click', this._onClickOutside);
        document.removeEventListener('keydown', this._onKeyDown);
    }

    _onContextMenu(e) {
        e.preventDefault();
        e.stopPropagation();

        if (!this.menuEl) {
            this._buildMenu();
        }

        this._updateItemStates();
        this._positionMenu(e.clientX, e.clientY);
        this._show();

        document.addEventListener('click', this._onClickOutside);
        document.addEventListener('keydown', this._onKeyDown);
    }

    _onClickOutside(e) {
        if (this.menuEl && !this.menuEl.contains(e.target)) {
            this._hide();
        }
    }

    _onKeyDown(e) {
        if (e.key === 'Escape') {
            this._hide();
        }
    }

    destroy() {
        this._hide();
        if (this.menuEl && this.menuEl.parentNode) {
            this.menuEl.parentNode.removeChild(this.menuEl);
        }
        this.menuEl = null;
        this.element.removeEventListener('contextmenu', this._onContextMenu);
    }
}

if (typeof window !== 'undefined') {
    window.PythraContextMenu = PythraContextMenuInternal;
    window.PythraContextMenuInternal = PythraContextMenuInternal;
}
