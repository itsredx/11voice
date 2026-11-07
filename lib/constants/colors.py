# ── Imports & Framework Colors ─────────────────────────────────────────
from pythra import Colors


# ── Studio Theme Colors ────────────────────────────────────────────────
class StudioColors:
    background = Colors.hex("#0F172A")        # Deep slate background
    surface = Colors.hex("#1E293B")           # Card / container surface
    surface_elevated = Colors.hex("#334155")  # Elevated borders & hover
    border = Colors.hex("#334155")
    
    primary = Colors.hex("#6366F1")           # Indigo primary accent
    primary_hover = Colors.hex("#4F46E5")
    
    speaker_a = Colors.hex("#38BDF8")         # Sky blue for Speaker A
    speaker_b = Colors.hex("#34D399")         # Emerald for Speaker B
    
    text_primary = Colors.hex("#F8FAFC")      # Bright white text
    text_secondary = Colors.hex("#94A3B8")    # Muted secondary text
    text_muted = Colors.hex("#64748B")        # Subtle captions
    
    active_turn_bg = Colors.hex("#1E1B4B")    # Glowing violet background for playing turn
    active_turn_border = Colors.hex("#818CF8")# Border highlight
    
    success = Colors.hex("#10B981")
    warning = Colors.hex("#F59E0B")
    error = Colors.hex("#EF4444")
