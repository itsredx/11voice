// clipPathUtils.js

/**
 * Parse an SVG path string containing absolute commands (M, L, A, H, V, Z),
 * and scale coordinates from reference dimensions to target dimensions.
 * 
 * @param {string} pathStr - Original SVG path string (absolute commands only)
 * @param {number} refW - reference width
 * @param {number} refH - reference height
 * @param {number} targetW - actual element width
 * @param {number} targetH - actual element height
 * @param {Object} [options] - optional settings:
 *    - {boolean} uniformArc
 *    - {number} decimalPlaces
 *    - {boolean} percentOutput
 * @returns {string} - scaled path string
 */
// clipPathUtils.js

export function scalePathAbsoluteMLA(pathStr, refW, refH, targetW, targetH, options = {}) {
  const rw = targetW / refW;
  const rh = targetH / refH;
  const uniformArc = !!options.uniformArc;
  const decimalPlaces = typeof options.decimalPlaces === 'number' ? options.decimalPlaces : null;
  const rScale = uniformArc ? Math.min(rw, rh) : null;

  const fmt = (num) => {
    return decimalPlaces !== null
      ? Number(num.toFixed(decimalPlaces)).toString()
      : Number(num).toString();
  };

  // Normalize the string
  const s = pathStr
    .replace(/,/g, ' ')
    .replace(/([0-9])-/g, '$1 -')
    .replace(/\s+/g, ' ')
    .trim();

  const tokenRegex = /([MLAZHV])|(-?\d*\.?\d+(?:e[-+]?\d+)?)/gi;
  const tokens = [];
  let match;
  while ((match = tokenRegex.exec(s)) !== null) {
    tokens.push(match[1] || match[2]);
  }

  const out = [];
  let i = 0;
  while (i < tokens.length) {
    const cmd = tokens[i++];
    out.push(cmd);

    switch (cmd) {
      case 'M':
      case 'L':
        while (i + 1 < tokens.length && !/^[MLAZHV]$/.test(tokens[i])) {
          const x = parseFloat(tokens[i++]) * rw;
          const y = parseFloat(tokens[i++]) * rh;
          out.push(fmt(x), fmt(y));
        }
        break;

      case 'A':
        while (i + 6 < tokens.length && !/^[MLAZHV]$/.test(tokens[i])) {
          const rx = parseFloat(tokens[i++]);
          const ry = parseFloat(tokens[i++]);
          const rot = tokens[i++];
          const laf = tokens[i++];
          const sf = tokens[i++];
          const x = parseFloat(tokens[i++]);
          const y = parseFloat(tokens[i++]);

          out.push(
            fmt(uniformArc ? rx * rScale : rx * rw),
            fmt(uniformArc ? ry * rScale : ry * rh),
            rot,
            laf,
            sf,
            fmt(x * rw),
            fmt(y * rh)
          );
        }
        break;

      case 'H':
        while (i < tokens.length && !/^[MLAZHV]$/.test(tokens[i])) {
          const x = parseFloat(tokens[i++]) * rw;
          out.push(fmt(x));
        }
        break;

      case 'V':
        while (i < tokens.length && !/^[MLAZHV]$/.test(tokens[i])) {
          const y = parseFloat(tokens[i++]) * rh;
          out.push(fmt(y));
        }
        break;

      case 'Z':
        // No coordinates to scale
        break;

      default:
        console.warn('Unsupported or unexpected token:', cmd);
    }
  }

  return out.join(' ');
}

export class ResponsiveClipPath {
  constructor(target, originalPath, refW, refH, options = {}) {
    this.elements = [];
    this.orig = originalPath.trim();
    this.refW = refW;
    this.refH = refH;
    this.options = options;
    this.currentPath = "";  // ⬅️ Store last computed path string
    this.update = this.update.bind(this);
    this.roList = [];

    this.isClassSelector = typeof target === 'string' && target.startsWith('.');
    this.selector = target;
    this.styleTagId = this.isClassSelector ? `clip-style-${target.substring(1)}` : null;

    if (this.isClassSelector) {
      let styleTag = document.getElementById(this.styleTagId);
      if (!styleTag) {
        styleTag = document.createElement('style');
        styleTag.id = this.styleTagId;
        document.head.appendChild(styleTag);
      }
      this.styleTag = styleTag;
    }

    if (typeof target === 'string') {
      let selector = target;
      if (!selector.startsWith('#') && !selector.startsWith('.')) {
        const byId = document.getElementById(selector);
        selector = byId ? `#${selector}` : `.${selector}`;
      }

      if (!this.isClassSelector && selector.startsWith('.')) {
        this.isClassSelector = true;
        this.selector = selector;
        this.styleTagId = `clip-style-${selector.substring(1)}`;
        let styleTag = document.getElementById(this.styleTagId);
        if (!styleTag) {
          styleTag = document.createElement('style');
          styleTag.id = this.styleTagId;
          document.head.appendChild(styleTag);
        }
        this.styleTag = styleTag;
      }

      const nodeList = document.querySelectorAll(selector);
      if (nodeList.length === 0) {
        console.warn(`ResponsiveClipPath: no elements found for selector "${selector}"`);
      }
      nodeList.forEach(el => this.elements.push(el));
      // console.log(`ResponsiveClipPath: Target "${target}" found ${this.elements.length} elements.`);
    } else if (target instanceof HTMLElement) {
      this.elements.push(target);
      // console.log(`ResponsiveClipPath: Target is HTMLElement. ID: ${target.id}`);
    } else {
      console.warn('ResponsiveClipPath: invalid target', target);
    }

    if (this.isClassSelector) {
      this.observeRepresentative();
    } else {
      this.elements.forEach(el => this.initElement(el));
    }
  }

  observeRepresentative() {
    if (this.classRo) return;

    let measureEl = this.elements[0];
    if (!measureEl || !measureEl.isConnected) {
      measureEl = document.querySelector(this.selector);
    }

    if (!measureEl) {
      setTimeout(() => this.observeRepresentative(), 100);
      return;
    }

    if (window.ResizeObserver) {
      this.classRo = new ResizeObserver(() => this.applyClassClip());
      this.classRo.observe(measureEl);
    } else {
      window.addEventListener('resize', this.update);
    }
  }

  applyClassClip() {
    // Find an element to measure
    let measureEl = this.elements[0];
    if (!measureEl || !measureEl.isConnected) {
      measureEl = document.querySelector(this.selector);
    }
    if (!measureEl) return;

    const rect = measureEl.getBoundingClientRect();
    if (rect.width === 0 || rect.height === 0) return;

    if (this.lastRect && this.lastRect.width === rect.width && this.lastRect.height === rect.height) {
      return;
    }
    this.lastRect = { width: rect.width, height: rect.height };

    const newPath = scalePathAbsoluteMLA(
      this.orig,
      this.refW,
      this.refH,
      rect.width,
      rect.height,
      this.options
    );
    this.currentPath = `path("${newPath}")`;

    if (this.styleTag) {
      this.styleTag.textContent = `
              ${this.selector} {
                  clip-path: ${this.currentPath} !important;
                  -webkit-clip-path: ${this.currentPath} !important;
              }
          `;
    }
  }

  initElement(el) {
    this.applyClip(el);
    if (window.ResizeObserver) {
      const ro = new ResizeObserver(() => this.applyClip(el));
      ro.observe(el);
      this.roList.push({ el, ro });
    } else {
      window.addEventListener('resize', this.update);
    }
  }

  applyClip(el) {
    const rect = el.getBoundingClientRect();
    // console.log(`ResponsiveClipPath.applyClip: ${el.id} Rect: ${rect.width}x${rect.height}`);
    const newPath = scalePathAbsoluteMLA(
      this.orig,
      this.refW,
      this.refH,
      rect.width,
      rect.height,
      this.options
    );
    this.currentPath = `path("${newPath}")`;  // ⬅️ Save it
    // console.log(`ResponsiveClipPath.applyClip: ${el.id} Path: ${this.currentPath}`);
    el.style.clipPath = this.currentPath;
    el.style.webkitClipPath = this.currentPath;
  }

  update() {
    if (this.isClassSelector) {
      this.applyClassClip();
    } else {
      this.elements.forEach(el => this.applyClip(el));
    }
  }

  disconnect() {
    this.roList.forEach(({ el, ro }) => ro.unobserve(el));
    this.roList = [];
    window.removeEventListener('resize', this.update);

    if (this.classRo) {
      this.classRo.disconnect();
      this.classRo = null;
    }

    if (this.styleTag && this.styleTag.parentNode) {
      this.styleTag.parentNode.removeChild(this.styleTag);
    }
  }

  // ✅ Your new method
  getResponsivePath() {
    return this.currentPath;
  }
}

window.ResponsiveClipPath = ResponsiveClipPath;
window.scalePathAbsoluteMLA = scalePathAbsoluteMLA;
