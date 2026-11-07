/**
 * PythraDropdown: Client-side engine for a custom Dropdown widget.
 *
 * Handles toggling the dropdown menu, closing it when clicking outside,
 * and sending the selected value back to the Python backend.
 */
export class PythraDropdown {
    constructor(elementId, options) {
        this.container = document.getElementById(elementId);
        if (!this.container) {
            console.error(`Dropdown container with ID #${elementId} not found.`);
            return;
        }

        console.log(`✅ PythraDropdown engine is initializing for #${elementId}`);

        this.options = options;
        this.valueContainer = this.container.querySelector('.dropdown-value-container');
        this.menu = this.container.querySelector('.dropdown-menu');
        this.items = this.menu.querySelectorAll('.dropdown-item');

        // Apply initial selected style
        const initialValue = this.options.selectedValue;
        if (initialValue !== undefined && initialValue !== null) {
            this.items.forEach(item => {
                if (item.dataset.value === String(initialValue)) {
                    item.classList.add('selected');
                }
            });
        }

        // Bind 'this' to maintain context in event handlers
        this.toggleMenu = this.toggleMenu.bind(this);
        this.handleItemClick = this.handleItemClick.bind(this);
        this.handleClickOutside = this.handleClickOutside.bind(this);

        // Attach event listeners
        this.valueContainer.addEventListener('click', this.toggleMenu);
        this.items.forEach(item => {
            item.addEventListener('click', this.handleItemClick);
        });
    }

    toggleMenu(event) {
        event.stopPropagation(); // Prevent click from bubbling to the document
        
        // Prevent opening if entire Dropdown is disabled
        if (this.container.classList.contains('disabled') || this.container.dataset.disabled === "true") {
            return;
        }

        const isCurrentlyOpen = this.container.classList.toggle('open');
        console.log("Value container Clicked");
        
        if (isCurrentlyOpen) {
            // If we just opened the menu, listen for clicks outside to close it
            document.addEventListener('click', this.handleClickOutside);
        } else {
            // If we just closed it, stop listening
            document.removeEventListener('click', this.handleClickOutside);
        }
    }

    handleItemClick(event) {
        // Find the actual dropdown item in case the user clicked a deeply nested child Widget
        const itemElement = event.currentTarget.closest('.dropdown-item') || event.currentTarget;
        
        // Prevent action if item represents a disabled DropdownMenuItem
        if (itemElement.classList.contains('disabled') || itemElement.dataset.disabled === "true") {
            event.stopPropagation();
            return;
        }

        const selectedValue = itemElement.dataset.value;
        const selectedLabel = itemElement.dataset.label || itemElement.textContent;

        console.log("Dropdown option Clicked");
        
        // 1. Update the display value immediately for instant feedback
        this.valueContainer.querySelector('span').textContent = selectedLabel;

        // 2. Update visual selection class
        this.items.forEach(item => item.classList.remove('selected'));
        itemElement.classList.add('selected');
        
        // 3. Send the selected *value* back to the Python backend
        if (window.pywebview && this.options.onChangedName) {
            window.pywebview.on_input_changed(this.options.onChangedName, selectedValue);
        }
        
        // 4. Close the menu
        this.closeMenu();
    }
    
    closeMenu() {
        if (this.container.classList.contains('open')) {
            this.container.classList.remove('open');
            document.removeEventListener('click', this.handleClickOutside);
        }
    }

    handleClickOutside(event) {
        // If the click is outside the main container, close the menu
        if (!this.container.contains(event.target)) {
            this.closeMenu();
        }
    }

    destroy() {
        // Cleanup to prevent memory leaks
        if (!this.container) return;
        this.valueContainer.removeEventListener('click', this.toggleMenu);
        this.items.forEach(item => {
            item.removeEventListener('click', this.handleItemClick);
        });
        document.removeEventListener('click', this.handleClickOutside);
    }
}