from pythra import Dropdown


class ScrollableDropdown(Dropdown):
    """Dropdown whose menu stays content-sized until it needs to scroll."""

    @staticmethod
    def generate_css_rule(style_key, css_class):
        css = Dropdown.generate_css_rule(style_key, css_class)
        selector = f".{css_class} .dropdown-menu {{"
        constrained_menu = (
            selector
            + "\n            height: auto;\n"
            + "            max-height: min(360px, 55vh);\n"
            + "            overflow-y: auto;"
        )
        return css.replace(selector, constrained_menu, 1)
