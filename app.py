import os
import json
import random
import datetime
from flask import Flask, render_template, request, jsonify, redirect, url_for, session
from dotenv import load_dotenv
from firebase_config import FIREBASE_WEB_CONFIG, init_firebase, get_db, verify_token

load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "cinegen-dev-secret")

ADMIN_EMAIL = "admin@gmail.com"

# Initialize Firebase
try:
    init_firebase()
    db = get_db()
    FIREBASE_READY = True
except Exception as e:
    print(f"[WARNING] Firebase Admin SDK not fully initialized: {e}")
    print("[INFO] App will still run; Firestore writes via client SDK (JS).")
    db = None
    FIREBASE_READY = False


# ─────────────────────────────────────────────
#  Auth helper
# ─────────────────────────────────────────────
def get_current_user():
    """Get user info from session."""
    return session.get("user")


def require_auth(f):
    """Decorator to protect routes."""
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("user"):
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated


def require_admin(f):
    """Decorator to protect admin-only routes."""
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        user = session.get("user")
        if not user:
            return redirect(url_for("login"))
        if not user.get("is_admin"):
            return redirect(url_for("dashboard"))
        return f(*args, **kwargs)
    return decorated


# ─────────────────────────────────────────────
#  PUBLIC PAGES
# ─────────────────────────────────────────────
@app.route("/")
def index():
    user = get_current_user()
    return render_template("index.html", user=user, firebase=FIREBASE_WEB_CONFIG)


@app.route("/login")
def login():
    if session.get("user"):
        return redirect(url_for("dashboard"))
    return render_template("login.html", firebase=FIREBASE_WEB_CONFIG)


@app.route("/register")
def register():
    if session.get("user"):
        return redirect(url_for("dashboard"))
    return render_template("register.html", firebase=FIREBASE_WEB_CONFIG)


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))


# ─────────────────────────────────────────────
#  AUTH API (called from JS after Firebase auth)
# ─────────────────────────────────────────────
@app.route("/api/auth/session", methods=["POST"])
def create_session():
    """Store user in Flask session after Firebase auth."""
    data = request.get_json()
    id_token = data.get("idToken")
    user_data = data.get("user", {})

    if not id_token:
        return jsonify({"error": "No token provided"}), 400

    # Try to verify token with Firebase Admin
    decoded = verify_token(id_token)
    uid = decoded.get("uid") if decoded else user_data.get("uid", "")

    # Check if user is blocked in Firebase Auth
    try:
        from firebase_admin import auth as fb_auth
        user_record = fb_auth.get_user(uid)
        if user_record.disabled:
            return jsonify({"error": "This account has been blocked by an administrator"}), 403
    except Exception as e:
        print(f"[Auth] Error checking user status: {e}")

    email = user_data.get("email", "")
    session["user"] = {
        "uid": uid,
        "email": email,
        "name": user_data.get("displayName") or user_data.get("name") or email.split("@")[0],
        "is_admin": email.lower() == ADMIN_EMAIL.lower(),
    }
    return jsonify({"status": "ok", "uid": uid, "is_admin": email.lower() == ADMIN_EMAIL.lower()})


@app.route("/api/auth/logout", methods=["POST"])
def api_logout():
    session.clear()
    return jsonify({"status": "ok"})


# ─────────────────────────────────────────────
#  USER DASHBOARD
# ─────────────────────────────────────────────
@app.route("/dashboard")
@require_auth
def dashboard():
    user = get_current_user()
    return render_template("dashboard.html", user=user, firebase=FIREBASE_WEB_CONFIG)


# ─────────────────────────────────────────────
#  CREATE STORY
# ─────────────────────────────────────────────
@app.route("/create-story")
@require_auth
def create_story():
    user = get_current_user()
    return render_template("create_story.html", user=user, firebase=FIREBASE_WEB_CONFIG)


@app.route("/api/generate/story", methods=["POST"])
def api_generate_story():
    """Generate a cinematic concept from user inputs."""
    data = request.get_json()
    genre = data.get("genre", "Drama")
    mood = data.get("mood", "Dark")
    audience = data.get("audience", "Adults")
    idea = data.get("idea", "")

    result = generate_story_concept(genre, mood, audience, idea)
    return jsonify(result)


def generate_story_concept(genre, mood, audience, idea):
    """Smart template-based story generation."""
    genres = {
        "Sci-Fi": ["a distant galaxy", "a dystopian future", "an abandoned space station", "a parallel universe"],
        "Thriller": ["a corrupt city", "an isolated mountain town", "a secret government facility", "a crumbling empire"],
        "Drama": ["a broken family estate", "an art-filled coastal city", "a fading small town", "a metropolitan hospital"],
        "Horror": ["a cursed coastal town", "an ancient asylum", "a remote winter cabin", "a haunted research lab"],
        "Romance": ["a sun-drenched Mediterranean city", "a rainy Paris street", "a quiet Japanese village", "a New York rooftop"],
        "Action": ["a war-torn city", "a criminal underworld", "an underground resistance network", "a global conspiracy hub"],
        "Comedy": ["a failing startup", "a chaotic wedding week", "a quirky small town", "a dysfunctional TV studio"],
    }
    moods_map = {
        "Dark": "brooding, heavy with moral ambiguity",
        "Hopeful": "quietly optimistic, building toward redemption",
        "Tense": "relentlessly tense, every silence loaded",
        "Melancholic": "achingly beautiful, laced with longing",
        "Epic": "sweeping and operatic in scope",
        "Mysterious": "enigmatic, where nothing is what it seems",
        "Uplifting": "warm and powerfully life-affirming",
    }
    arcs = [
        ["Ordinary world established", "Inciting incident disrupts status quo", "Protagonist refuses the call", "Mentor arrives", "Crossing the threshold", "Tests, allies, enemies", "Ordeal & revelation", "Transformation & resolution"],
        ["In medias res — story begins mid-crisis", "Flashback exposition", "Rising stakes", "False victory", "Dark night of the soul", "Climactic confrontation", "Denouement"],
        ["Multiple parallel storylines introduced", "Threads intersect unexpectedly", "Central conflict emerges", "Crisis point fractures relationships", "Convergence & climax", "Earned resolution"],
    ]
    visual_styles = {
        "Dark": "Desaturated palette with isolated pools of warm light. Inspired by *Blade Runner 2049* and *No Country for Old Men*.",
        "Hopeful": "Golden hour cinematography, shallow depth of field. Inspired by *Nomadland* and *The Tree of Life*.",
        "Tense": "Tight, handheld close-ups, claustrophobic framing. Inspired by *Uncut Gems* and *1917*.",
        "Melancholic": "Soft blues and greens, slow drifting camera. Inspired by *Her* and *Lost in Translation*.",
        "Epic": "Wide anamorphic lenses, vast landscapes, dramatic orchestral cues. Inspired by *Dune* and *Lawrence of Arabia*.",
        "Mysterious": "Deep shadows, fog, symmetrical framing. Inspired by *Parasite* and *Mulholland Drive*.",
        "Uplifting": "Vibrant natural light, energetic cuts, warm color grading. Inspired by *Whiplash* and *Julie & Julia*.",
    }

    setting = random.choice(genres.get(genre, ["an unnamed world"]))
    mood_desc = moods_map.get(mood, "emotionally resonant")
    arc = random.choice(arcs)
    visual = visual_styles.get(mood, "A distinctive cinematic aesthetic.")

    idea_core = idea.strip() if idea.strip() else f"a profound journey of self-discovery against impossible odds"

    return {
        "logline": f"In {setting}, {idea_core} — a {mood_desc} {genre} story for {audience}.",
        "synopsis": (
            f"Set against the backdrop of {setting}, this {genre} story unfolds as {idea_core}. "
            f"The narrative is {mood_desc}, drawing the audience into a world where every choice carries weight. "
            f"As the protagonist is pushed to their limits, themes of identity, sacrifice, and resilience emerge. "
            f"The story reaches its emotional apex in a climax that redefines everything that came before, "
            f"leaving the audience with a lasting impression that transcends genre."
        ),
        "characters": [
            {"name": "The Protagonist", "archetype": "Flawed Hero", "core_want": "Freedom from their past", "core_need": "To accept vulnerability"},
            {"name": "The Antagonist", "archetype": "Mirror of the Protagonist", "core_want": "Control and order", "core_need": "To be understood"},
            {"name": "The Ally", "archetype": "Loyal Skeptic", "core_want": "Protect those they love", "core_need": "To believe in something larger"},
        ],
        "story_arc": arc,
        "visual_style": visual,
        "genre": genre,
        "mood": mood,
        "target_audience": audience,
    }


# ─────────────────────────────────────────────
#  CHARACTER GENERATOR
# ─────────────────────────────────────────────
@app.route("/characters")
@require_auth
def characters():
    user = get_current_user()
    return render_template("characters.html", user=user, firebase=FIREBASE_WEB_CONFIG)


@app.route("/api/generate/characters", methods=["POST"])
def api_generate_characters():
    data = request.get_json()
    summary = data.get("summary", "")
    genre = data.get("genre", "Drama")
    num = int(data.get("count", 4))

    chars = generate_characters(summary, genre, num)
    return jsonify({"characters": chars})


def generate_characters(summary, genre, num=4):
    archetypes = [
        {"archetype": "The Reluctant Hero", "personality": "Introspective, fiercely loyal, haunted by past failure", "motivation": "Redemption for a past mistake", "conflict": "Believes they are not worthy of the role thrust upon them", "role": "Protagonist"},
        {"archetype": "The Shadow", "personality": "Brilliant, charismatic, morally flexible", "motivation": "Absolute control over a flawed system", "conflict": "Genuinely believes they are the hero of their own story", "role": "Antagonist"},
        {"archetype": "The Oracle", "personality": "Cryptic, empathetic, burdened by knowledge", "motivation": "Ensure the right outcome — whatever the cost", "conflict": "Cannot interfere directly without breaking a sacred oath", "role": "Mentor"},
        {"archetype": "The Loyal Skeptic", "personality": "Sharp, pragmatic, deeply caring beneath cynicism", "motivation": "Protect the people they consider family", "conflict": "Loyalty vs. personal moral code", "role": "Ally"},
        {"archetype": "The Catalyst", "personality": "Unpredictable, passionate, a force of nature", "motivation": "Disrupt the status quo at any cost", "conflict": "Cannot distinguish between righteous chaos and destruction", "role": "Wildcard"},
        {"archetype": "The Mirror", "personality": "Gentle, perceptive, deeply principled", "motivation": "Show the protagonist who they truly are", "conflict": "Bears the consequences of the protagonist's choices", "role": "Foil"},
    ]
    names_pool = [
        ("Elara Voss", 32), ("Marcus Thein", 45), ("Sable Ren", 28), ("Dorian Cross", 55),
        ("Nia Okafor", 34), ("Cassius Wren", 38), ("Petra Kade", 27), ("Lucius Mara", 62),
        ("Zoya Stirling", 30), ("Fenris Cole", 41), ("Lena Arquette", 26), ("Rhett Solano", 49),
    ]

    result = []
    random.shuffle(archetypes)
    random.shuffle(names_pool)

    for i in range(min(num, len(archetypes))):
        name, age = names_pool[i] if i < len(names_pool) else (f"Character {i+1}", 30)
        arch = archetypes[i]
        result.append({
            "name": name,
            "age": age,
            "archetype": arch["archetype"],
            "personality": arch["personality"],
            "motivation": arch["motivation"],
            "conflict": arch["conflict"],
            "role": arch["role"],
        })
    return result


# ─────────────────────────────────────────────
#  SCENE BUILDER
# ─────────────────────────────────────────────
@app.route("/scene-builder")
@require_auth
def scene_builder():
    user = get_current_user()
    return render_template("scene_builder.html", user=user, firebase=FIREBASE_WEB_CONFIG)


@app.route("/api/generate/scenes", methods=["POST"])
def api_generate_scenes():
    data = request.get_json()
    logline = data.get("logline", "")
    genre = data.get("genre", "Drama")

    scenes = generate_scenes(logline, genre)
    return jsonify({"scenes": scenes})


def generate_scenes(logline, genre):
    return [
        {"type": "Opening Scene", "title": "Establishing the World", "content": f"Wide establishing shots introduce the world of our story. The visual grammar is set — colour palette, rhythm of editing, sound design. We meet our protagonist in their ordinary world, unaware of what's coming. A quiet moment loaded with subtext.", "icon": "🌅"},
        {"type": "Inciting Incident", "title": "The World Shifts", "content": "An event shatters the protagonist's routine. There is no going back. The central question of the film is posed — not in dialogue, but in action and consequence. The audience leans forward.", "icon": "⚡"},
        {"type": "Rising Tension", "title": "The Long Road", "content": "A series of escalating obstacles tests the protagonist's resolve. Each failure costs something real. Alliances form and fracture. The antagonistic force tightens its grip. The midpoint brings a false victory — or a devastating loss.", "icon": "📈"},
        {"type": "Climax", "title": "The Point of No Return", "content": "Everything converges. The protagonist faces their greatest fear — not the external villain, but the internal lie they've been living. A choice must be made. The outcome of this moment will determine who they truly are.", "icon": "🔥"},
        {"type": "Resolution", "title": "A New World", "content": "The dust settles. The world looks the same, but everything has changed. We see our protagonist — transformed. The final image echoes the opening, but recontextualised. A feeling lingers long after the credits roll.", "icon": "🌙"},
    ]


# ─────────────────────────────────────────────
#  SOUNDTRACK ASSISTANT
# ─────────────────────────────────────────────
@app.route("/soundtrack")
@require_auth
def soundtrack():
    user = get_current_user()
    return render_template("soundtrack.html", user=user, firebase=FIREBASE_WEB_CONFIG)


@app.route("/api/generate/soundtrack", methods=["POST"])
def api_generate_soundtrack():
    data = request.get_json()
    genre = data.get("genre", "Drama")
    mood = data.get("mood", "Dark")
    key_scene = data.get("key_scene", "Climax")

    result = generate_soundtrack(genre, mood, key_scene)
    return jsonify(result)


def generate_soundtrack(genre, mood, key_scene):
    score_styles = {
        "Dark": "Sparse, minimalist orchestral score with long held strings and dissonant brass stabs. Silence used as a weapon.",
        "Hopeful": "Swelling strings over solo piano motif. Simple, earnest, emotionally devastating in its restraint.",
        "Tense": "Micro-tonal string clusters, irregular percussion, no melodic resolution. Bernard Herrmann meets Ennio Morricone.",
        "Melancholic": "Solo cello or violin over ambient bed. Slow harmonic movement, space between notes as important as notes themselves.",
        "Epic": "Full orchestra with choir. Leitmotifs introduced for each major character. Thunderous climax, quiet denouement.",
        "Mysterious": "Prepared piano, eerie windchimes, sustained synth pads. Tonal ambiguity throughout.",
        "Uplifting": "Acoustic guitar, bright brass fanfares, building to full orchestral swell. Rhythmically vital and life-affirming.",
    }
    instruments_map = {
        "Dark": ["Cello ensemble", "Bass clarinet", "Contrabassoon", "Low brass", "Prepared piano", "Sub-bass synth"],
        "Hopeful": ["Solo piano", "Violin section", "French horns", "Woodwind choir", "Acoustic guitar"],
        "Tense": ["String quartet", "Percussion ensemble", "Brass stabs", "Double bass", "Electronic textures"],
        "Melancholic": ["Solo cello", "Ambient synth pads", "Acoustic piano", "Viola section"],
        "Epic": ["Full orchestra", "Mixed choir", "Pipe organ", "Taiko drums", "Brass ensemble"],
        "Mysterious": ["Prepared piano", "Glass harmonica", "Theremin", "Crystal bowls", "Solo violin harmonics"],
        "Uplifting": ["Acoustic guitar", "Trumpet section", "Full strings", "Woodwinds", "Grand piano"],
    }
    placements = {
        "Opening Scene": "Subtle ambient underscore — let the visuals breathe. Music enters only after 90 seconds.",
        "Inciting Incident": "Music enters abruptly mid-scene. A simple two-note motif that will recur throughout.",
        "Rising Tension": "Ostinato builds progressively. Layering instruments every 30 seconds. No resolution.",
        "Climax": "Full score — maximum emotional and sonic intensity. The main theme finally heard in full.",
        "Resolution": "Echo of the opening theme, now reharmonised. Fades into silence, then one final note.",
    }

    return {
        "score_style": score_styles.get(mood, "Cinematic orchestral score."),
        "instruments": instruments_map.get(mood, ["Full orchestra"]),
        "song_placement": placements.get(key_scene, "Score enters at the emotional peak of the scene."),
        "emotional_intent": f"The music should make the audience feel the full weight of the {mood.lower()} atmosphere — before, during, and after the {key_scene.lower()}.",
        "reference_composers": get_reference_composers(mood),
        "tempo": get_tempo(mood),
        "key": get_suggested_key(mood),
    }


def get_reference_composers(mood):
    refs = {
        "Dark": ["Jóhann Jóhannsson", "Ennio Morricone", "Nick Cave & Warren Ellis"],
        "Hopeful": ["Alexandre Desplat", "Michael Giacchino", "John Williams"],
        "Tense": ["Bernard Herrmann", "Clint Mansell", "Trent Reznor & Atticus Ross"],
        "Melancholic": ["Ryuichi Sakamoto", "Ólafur Arnalds", "Max Richter"],
        "Epic": ["Hans Zimmer", "Howard Shore", "John Powell"],
        "Mysterious": ["Angelo Badalamenti", "Jonny Greenwood", "Mica Levi"],
        "Uplifting": ["Thomas Newman", "Joe Hisaishi", "Patrick Doyle"],
    }
    return refs.get(mood, ["Hans Zimmer", "John Williams"])


def get_tempo(mood):
    tempos = {"Dark": "♩= 40–55 BPM (largo)", "Hopeful": "♩= 72–84 BPM (andante)", "Tense": "♩= 120–144 BPM (allegro agitato)", "Melancholic": "♩= 52–66 BPM (adagio)", "Epic": "♩= 60–80 BPM (maestoso)", "Mysterious": "♩= 48–60 BPM (lento)", "Uplifting": "♩= 100–120 BPM (allegretto)"}
    return tempos.get(mood, "♩= 72 BPM")


def get_suggested_key(mood):
    keys = {"Dark": "D minor / B♭ minor", "Hopeful": "D major / G major", "Tense": "C# minor (atonal passages)", "Melancholic": "E minor / A minor", "Epic": "C major / F major", "Mysterious": "F# minor (chromatic)", "Uplifting": "G major / E major"}
    return keys.get(mood, "D minor")


# ─────────────────────────────────────────────
#  MY SCRIPTS
# ─────────────────────────────────────────────
@app.route("/my-scripts")
@require_auth
def my_scripts():
    user = get_current_user()
    return render_template("my_scripts.html", user=user, firebase=FIREBASE_WEB_CONFIG)


# ─────────────────────────────────────────────
#  ADMIN DASHBOARD
# ─────────────────────────────────────────────
@app.route("/admin")
@require_admin
def admin():
    user = get_current_user()
    return render_template("admin.html", user=user, firebase=FIREBASE_WEB_CONFIG)


@app.route("/api/admin/users")
def api_admin_users():
    """Return all registered users from Firebase Auth with their script counts."""
    user = session.get("user")
    if not user or not user.get("is_admin"):
        return jsonify({"error": "Unauthorized"}), 403

    users_list = []
    try:
        from firebase_admin import auth as fb_auth
        
        # Cache script counts to avoid N+1 queries
        script_counts = {}
        if db and FIREBASE_READY:
            scripts = db.collection("scripts").stream()
            for s in scripts:
                uid = s.to_dict().get("uid")
                if uid:
                    script_counts[uid] = script_counts.get(uid, 0) + 1

        page = fb_auth.list_users()
        while page:
            for u in page.users:
                users_list.append({
                    "uid": u.uid,
                    "email": u.email or "",
                    "name": u.display_name or (u.email.split("@")[0] if u.email else "Unknown"),
                    "created_at": int(u.user_metadata.creation_timestamp) if u.user_metadata and u.user_metadata.creation_timestamp else None,
                    "last_login": int(u.user_metadata.last_sign_in_timestamp) if u.user_metadata and u.user_metadata.last_sign_in_timestamp else None,
                    "email_verified": u.email_verified,
                    "provider": u.provider_data[0].provider_id if u.provider_data else "password",
                    "photo_url": u.photo_url or "",
                    "disabled": u.disabled,
                    "scripts_count": script_counts.get(u.uid, 0)
                })
            page = page.get_next_page()
    except Exception as e:
        print(f"[Admin] User registry error: {e}")
        return jsonify({"users": [], "error": str(e)})

    return jsonify(users_list)


@app.route("/api/admin/promote", methods=["POST"])
@require_admin
def api_admin_promote():
    """Placeholder for promoting users to admin."""
    data = request.json
    uid = data.get("uid")
    # In a real app, you'd set custom claims here
    return jsonify({"status": "ok", "message": f"Promotion request for {uid} received."})


@app.route("/api/admin/toggle-block", methods=["POST"])
@require_admin
def api_toggle_block_user():
    """Block or unblock a user (admin only)."""
    data = request.get_json()
    uid = data.get("uid")
    block = data.get("block", True)

    if not uid:
        return jsonify({"error": "No UID provided"}), 400

    if uid == session.get("user", {}).get("uid"):
        return jsonify({"error": "You cannot block yourself"}), 400

    try:
        from firebase_admin import auth as fb_auth
        fb_auth.update_user(uid, disabled=block)
        return jsonify({"status": "ok", "disabled": block})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/admin/stats")
@require_admin
def api_admin_stats():
    """Return advanced admin statistics for the analytics dashboard."""
    if db and FIREBASE_READY:
        try:
            from datetime import datetime, date
            today_start = datetime.combine(date.today(), datetime.min.time()).timestamp() * 1000

            scripts_ref = db.collection("scripts")
            scripts = scripts_ref.stream()

            genres = {}
            moods = {}
            daily_stats = {}  # {date_str: count}
            total_scripts = 0
            scripts_today = 0

            for s in scripts:
                data = s.to_dict()
                total_scripts += 1
                
                # Today's output
                ts = data.get("created_at")
                if ts:
                    # Handle Firestore Timestamp vs Numeric
                    val = ts.timestamp() * 1000 if hasattr(ts, 'timestamp') else ts
                    if val >= today_start:
                        scripts_today += 1

                # Genre distribution
                gen = data.get("genre", "Unknown")
                genres[gen] = genres.get(gen, 0) + 1

                # Mood distribution
                md = data.get("mood", "Neutral")
                moods[md] = moods.get(md, 0) + 1

                # Trends
                if ts:
                    dt = ts if hasattr(ts, 'timestamp') else datetime.fromtimestamp(ts / 1000)
                    date_str = dt.strftime("%Y-%m-%d")
                    daily_stats[date_str] = daily_stats.get(date_str, 0) + 1

            # Format trends
            sorted_dates = sorted(daily_stats.keys())
            chart_trends = {
                "labels": sorted_dates[-7:],
                "data": [daily_stats[d] for d in sorted_dates[-7:]]
            }

            top_mood = max(moods, key=moods.get) if moods else "None"

            return jsonify({
                "total_scripts": total_scripts,
                "scripts_today": scripts_today,
                "genre_stats": genres,
                "mood_stats": moods,
                "top_mood": top_mood,
                "trends": chart_trends,
                "total_users": 0, # Frontend will fill from users API
                "active_today": 0
            })
        except Exception as e:
            print(f"[Admin] Stats Error: {e}")
    return jsonify({"total_scripts": 0, "genre_stats": {}, "mood_stats": {}, "trends": {"labels": [], "data": []}})


# ─────────────────────────────────────────────
#  SETTINGS
# ─────────────────────────────────────────────
@app.route("/settings")
@require_auth
def settings():
    user = get_current_user()
    return render_template("settings.html", user=user, firebase=FIREBASE_WEB_CONFIG)


# ─────────────────────────────────────────────
#  ERROR HANDLERS
# ─────────────────────────────────────────────
@app.errorhandler(404)
def not_found(e):
    return render_template("404.html"), 404


@app.errorhandler(500)
def server_error(e):
    return render_template("404.html"), 500


@app.route("/api/scripts/<script_id>/pdf")
@require_auth
def export_script_pdf(script_id):
    """Generate a professional PDF for a specific script."""
    user = get_current_user()
    if not db or not FIREBASE_READY:
        return jsonify({"error": "Database not available"}), 500

    try:
        from fpdf import FPDF
        
        doc_ref = db.collection("scripts").document(script_id)
        script_data = doc_ref.get()
        
        if not script_data.exists:
            return jsonify({"error": "Script not found"}), 404
            
        data = script_data.to_dict()
        
        # Security check: Ensure user owns the script
        if data.get("uid") != user["uid"]:
            return jsonify({"error": "Unauthorized"}), 403

        class ScriptPDF(FPDF):
            def header(self):
                if self.page_no() > 1:
                    self.set_font("Courier", "I", 8)
                    self.cell(0, 10, f"{data.get('title', 'Untitled').upper()} - Concept Brief", align="R")
                    self.ln(10)

            def footer(self):
                self.set_y(-15)
                self.set_font("Courier", "I", 8)
                self.cell(0, 10, f"Page {self.page_no()}", align="C")

        pdf = ScriptPDF()
        pdf.add_page()
        pdf.set_font("Courier", "B", 24)
        
        # Title Page
        pdf.ln(60)
        pdf.cell(0, 20, data.get("title", "UNTITLED CONCEPT").upper(), align="C")
        pdf.ln(10)
        pdf.set_font("Courier", "", 12)
        pdf.cell(0, 10, f"A {data.get('genre', 'Drama')} Story", align="C")
        pdf.ln(40)
        
        pdf.set_font("Courier", "B", 12)
        pdf.cell(0, 10, "CONCEPT BY", align="C")
        pdf.ln(10)
        pdf.set_font("Courier", "", 12)
        pdf.cell(0, 10, user.get("name", "CineGen Filmmaker"), align="C")
        
        pdf.ln(60)
        pdf.set_font("Courier", "I", 10)
        pdf.cell(0, 10, f"Generated via CineGen AI — {datetime.date.today().strftime('%B %d, %Y')}", align="C")

        # Details Page
        pdf.add_page()
        
        # Logline
        pdf.set_font("Courier", "B", 14)
        pdf.cell(0, 10, "I. LOGLINE")
        pdf.ln(12)
        pdf.set_font("Courier", "", 12)
        pdf.multi_cell(0, 8, data.get("logline", "No logline provided."))
        pdf.ln(10)

        # Synopsis
        pdf.set_font("Courier", "B", 14)
        pdf.cell(0, 10, "II. SYNOPSIS")
        pdf.ln(12)
        pdf.set_font("Courier", "", 12)
        pdf.multi_cell(0, 8, data.get("synopsis", "No synopsis provided."))
        pdf.ln(10)

        # Characters
        pdf.set_font("Courier", "B", 14)
        pdf.cell(0, 10, "III. DRAMATIS PERSONAE")
        pdf.ln(12)
        for char in data.get("characters", []):
            pdf.set_font("Courier", "B", 12)
            pdf.cell(0, 8, f"{char.get('name', 'Unknown').upper()} — {char.get('archetype', 'Archetype')}")
            pdf.ln(8)
            pdf.set_font("Courier", "", 11)
            pdf.multi_cell(0, 6, f"Want: {char.get('core_want', 'N/A')}\nNeed: {char.get('core_need', 'N/A')}")
            pdf.ln(6)

        # Story Arc
        pdf.add_page()
        pdf.set_font("Courier", "B", 14)
        pdf.cell(0, 10, "IV. NARRATIVE ARC")
        pdf.ln(12)
        pdf.set_font("Courier", "", 12)
        for i, beat in enumerate(data.get("story_arc", [])):
            pdf.multi_cell(0, 8, f"{i+1}. {beat}")
            pdf.ln(4)
        pdf.ln(10)

        # Visual Style
        pdf.set_font("Courier", "B", 14)
        pdf.cell(0, 10, "V. VISUAL GRAMMAR")
        pdf.ln(12)
        pdf.set_font("Courier", "", 12)
        pdf.multi_cell(0, 8, data.get("visual_style", "A distinctive cinematic aesthetic."))

        from flask import make_response
        response = make_response(pdf.output())
        response.headers.set('Content-Type', 'application/pdf')
        response.headers.set('Content-Disposition', 'attachment', filename=f"{data.get('title', 'script')}.pdf")
        return response

    except Exception as e:
        print(f"[Export] PDF Error: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/admin/scripts")
@require_admin
def api_admin_scripts():
    """Return all scripts across the platform (admin only)."""
    if db and FIREBASE_READY:
        try:
            scripts_ref = db.collection("scripts")
            # Ordering by created_at desc to show latest first
            scripts = scripts_ref.order_by("created_at", direction="DESCENDING").limit(100).stream()
            
            scripts_list = []
            for s in scripts:
                data = s.to_dict()
                scripts_list.append({
                    "id": s.id,
                    "title": data.get("title", "Untitled"),
                    "genre": data.get("genre", "Drama"),
                    "mood": data.get("mood", "Neutral"),
                    "creator_email": data.get("creator_email", "Unknown"),
                    "created_at": data.get("created_at"),
                    "content_preview": (data.get("script_content", "")[:200] + "...") if data.get("script_content") else "No content available."
                })
            return jsonify({"scripts": scripts_list})
        except Exception as e:
            print(f"[Admin] Scripts registry error: {e}")
    return jsonify({"scripts": [], "error": "Database not initialized or query failed"})


if __name__ == "__main__":
    app.run(debug=os.environ.get("FLASK_DEBUG", "True") == "True", port=5000)
