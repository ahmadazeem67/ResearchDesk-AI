"""
styles.py
---------
Visual identity: "The Research Desk."

Rationale (see frontend-design skill): rather than the generic AI-chat
defaults (dark slate + violet gradient, or cream + terracotta), this app
leans into its actual context — a study/research assistant being demoed
in an academic setting. The palette borrows from library reading rooms:
deep ink-navy, brass/warm-gold accents, parchment surfaces in light mode.
Headers use a serif display face (Source Serif 4) for academic gravitas;
UI chrome uses a clean grotesque (Inter) so controls stay legible at small
sizes. The signature element is the message bubble treatment: assistant
messages read like annotated index cards with a left accent rule and a
small serif "marginalia" label, instead of generic rounded chat bubbles.
"""

LIGHT_VARS = """
    --bg-primary: #F7F3EA;
    --bg-secondary: #FFFFFF;
    --bg-sidebar: #EFE8D8;
    --bg-card: #FFFFFF;
    --bg-input: #FFFFFF;
    --text-primary: #1B2430;
    --text-secondary: #5B5447;
    --text-muted: #8A8270;
    --accent: #8B5E1F;
    --accent-strong: #6B4513;
    --accent-soft: #E8D9B8;
    --ink: #1B2430;
    --user-bubble: #1B2430;
    --user-bubble-text: #F7F3EA;
    --ai-card: #FFFFFF;
    --border: #DDD3BB;
    --shadow: rgba(27, 36, 48, 0.08);
    --success: #3F7D55;
    --danger: #B0473E;
"""

DARK_VARS = """
    --bg-primary: #11151C;
    --bg-secondary: #161B24;
    --bg-sidebar: #0D1117;
    --bg-card: #1B212C;
    --bg-input: #1B212C;
    --text-primary: #EDEAE1;
    --text-secondary: #ABA690;
    --text-muted: #6E7385;
    --accent: #D4A24C;
    --accent-strong: #E8BF73;
    --accent-soft: #2A2515;
    --ink: #EDEAE1;
    --user-bubble: #D4A24C;
    --user-bubble-text: #11151C;
    --ai-card: #1B212C;
    --border: #2A3140;
    --shadow: rgba(0, 0, 0, 0.4);
    --success: #5FAE78;
    --danger: #E1645A;
"""


def build_css(theme: str) -> str:
    vars_block = DARK_VARS if theme == "dark" else LIGHT_VARS
    return f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Source+Serif+4:opsz,wght@8..60,400;8..60,600;8..60,700&family=Inter:wght@400;500;600;700&display=swap');

:root {{
{vars_block}
}}

html, body, [class*="css"] {{
    font-family: 'Inter', sans-serif;
}}

/* ---------- App shell ---------- */
.stApp {{
    background: var(--bg-primary);
    color: var(--text-primary);
    transition: background 0.3s ease, color 0.3s ease;
}}

[data-testid="stHeader"] {{
    background: transparent;
}}

section[data-testid="stSidebar"] {{
    background: var(--bg-sidebar);
    border-right: 1px solid var(--border);
}}

section[data-testid="stSidebar"] > div {{
    padding-top: 1rem;
}}

/* ---------- Top brand bar ---------- */
.brand-bar {{
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0.85rem 1.4rem;
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: 14px;
    margin-bottom: 1.1rem;
    box-shadow: 0 2px 10px var(--shadow);
}}

.brand-title {{
    font-family: 'Source Serif 4', serif;
    font-weight: 700;
    font-size: 1.35rem;
    color: var(--text-primary);
    letter-spacing: -0.01em;
    display: flex;
    align-items: center;
    gap: 0.55rem;
}}

.brand-mark {{
    color: var(--accent);
}}

.chat-name-pill {{
    font-size: 0.82rem;
    color: var(--text-secondary);
    background: var(--accent-soft);
    border-radius: 999px;
    padding: 0.3rem 0.85rem;
    font-family: 'Inter', sans-serif;
}}

/* ---------- Sidebar sections ---------- */
.sidebar-eyebrow {{
    font-family: 'Inter', sans-serif;
    font-size: 0.7rem;
    font-weight: 700;
    letter-spacing: 0.09em;
    text-transform: uppercase;
    color: var(--text-muted);
    margin: 1.1rem 0 0.45rem 0.1rem;
}}

.chat-row {{
    border-radius: 10px;
    padding: 0.5rem 0.65rem;
    margin-bottom: 0.25rem;
    border: 1px solid transparent;
}}

.chat-row:hover {{
    background: var(--accent-soft);
}}

.chat-row-active {{
    background: var(--accent-soft);
    border: 1px solid var(--accent);
}}

.chat-title-text {{
    font-size: 0.88rem;
    font-weight: 500;
    color: var(--text-primary);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}}

.chat-meta-text {{
    font-size: 0.72rem;
    color: var(--text-muted);
}}

.pin-badge {{
    color: var(--accent);
    font-size: 0.75rem;
}}

/* ---------- Message cards (signature element) ---------- */
.msg-row {{
    display: flex;
    margin-bottom: 0.95rem;
    animation: fadeSlideIn 0.25s ease;
}}

@keyframes fadeSlideIn {{
    from {{ opacity: 0; transform: translateY(6px); }}
    to {{ opacity: 1; transform: translateY(0); }}
}}

.msg-row.user {{
    justify-content: flex-end;
}}

.msg-row.assistant {{
    justify-content: flex-start;
}}

.bubble-user {{
    background: var(--user-bubble);
    color: var(--user-bubble-text);
    border-radius: 16px 16px 4px 16px;
    padding: 0.7rem 1.05rem;
    max-width: 72%;
    font-size: 0.95rem;
    line-height: 1.5;
    box-shadow: 0 2px 8px var(--shadow);
}}

.card-assistant {{
    background: var(--ai-card);
    border: 1px solid var(--border);
    border-left: 3px solid var(--accent);
    border-radius: 4px 14px 14px 14px;
    padding: 0.85rem 1.1rem 0.7rem 1.1rem;
    max-width: 78%;
    box-shadow: 0 2px 10px var(--shadow);
}}

.marginalia {{
    font-family: 'Source Serif 4', serif;
    font-style: italic;
    font-size: 0.74rem;
    color: var(--accent);
    margin-bottom: 0.3rem;
    letter-spacing: 0.02em;
}}

.card-assistant-body {{
    font-size: 0.95rem;
    line-height: 1.6;
    color: var(--text-primary);
}}

.card-assistant-body p {{
    margin: 0 0 0.6em 0;
}}

.card-assistant-body code {{
    background: var(--accent-soft);
    padding: 0.15rem 0.4rem;
    border-radius: 4px;
    font-size: 0.85em;
}}

.card-assistant-body pre {{
    background: var(--bg-sidebar);
    border-radius: 8px;
    padding: 0.8rem;
    overflow-x: auto;
}}

/* ---------- Suggested prompts ---------- */
.prompt-chip {{
    display: inline-block;
    background: var(--bg-card);
    border: 1px solid var(--border);
    color: var(--text-secondary);
    border-radius: 999px;
    padding: 0.4rem 0.95rem;
    font-size: 0.82rem;
    margin: 0.2rem 0.3rem 0.2rem 0;
}}

/* ---------- Stat cards ---------- */
.stat-card {{
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: 14px;
    padding: 1.1rem 1.2rem;
    box-shadow: 0 2px 10px var(--shadow);
}}

.stat-number {{
    font-family: 'Source Serif 4', serif;
    font-size: 2.1rem;
    font-weight: 700;
    color: var(--accent-strong);
    line-height: 1;
}}

.stat-label {{
    font-size: 0.78rem;
    color: var(--text-muted);
    text-transform: uppercase;
    letter-spacing: 0.06em;
    margin-top: 0.3rem;
}}

/* ---------- Misc ---------- */
hr {{
    border-color: var(--border);
}}

.thinking-dots span {{
    animation: blink 1.4s infinite both;
    font-size: 1.1rem;
    color: var(--accent);
}}
.thinking-dots span:nth-child(2) {{ animation-delay: 0.2s; }}
.thinking-dots span:nth-child(3) {{ animation-delay: 0.4s; }}

@keyframes blink {{
    0%, 80%, 100% {{ opacity: 0; }}
    40% {{ opacity: 1; }}
}}

div[data-testid="stChatInput"] textarea {{
    border-radius: 14px !important;
}}

.stButton button {{
    border-radius: 9px;
}}

/* Scrollbar */
::-webkit-scrollbar {{ width: 8px; height: 8px; }}
::-webkit-scrollbar-thumb {{ background: var(--border); border-radius: 8px; }}
::-webkit-scrollbar-track {{ background: transparent; }}

</style>
"""